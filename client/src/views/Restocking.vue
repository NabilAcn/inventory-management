<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetLabel') }}</h3>
          <span class="full-cost">{{ t('restocking.fullRestockCost', { amount: money(fullRestockCost) }) }}</span>
        </div>
        <div class="slider-wrap">
          <div class="slider-value">{{ money(budget) }}</div>
          <input
            v-model.number="budget"
            type="range"
            class="budget-slider"
            min="0"
            :max="sliderMax"
            :step="sliderStep"
            :style="{ '--fill': fillPercent + '%' }"
            :aria-label="t('restocking.budgetLabel')"
            :disabled="submitting"
          />
          <div class="slider-scale">
            <span>{{ money(0) }}</span>
            <span>{{ money(sliderMax) }}</span>
          </div>
        </div>
      </div>

      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-label">{{ t('restocking.budget') }}</div>
          <div class="summary-value">{{ money(budget) }}</div>
        </div>
        <div class="summary-card accent">
          <div class="summary-label">{{ t('restocking.estimatedSpend') }}</div>
          <div class="summary-value">{{ money(estimatedSpend) }}</div>
        </div>
        <div class="summary-card positive">
          <div class="summary-label">{{ t('restocking.remaining') }}</div>
          <div class="summary-value">{{ money(remainingBudget) }}</div>
        </div>
      </div>

      <div v-if="confirmation" class="confirmation" role="status">
        <h3>{{ t('restocking.confirmation.title') }}</h3>
        <dl class="confirmation-grid">
          <div>
            <dt>{{ t('restocking.confirmation.orderId') }}</dt>
            <dd>{{ confirmation.id }}</dd>
          </div>
          <div>
            <dt>{{ t('restocking.confirmation.total') }}</dt>
            <dd>{{ money(confirmation.total_cost, 2) }}</dd>
          </div>
          <div>
            <dt>{{ t('restocking.confirmation.leadTime') }}</dt>
            <dd>{{ confirmation.lead_time_days }} {{ t('restocking.confirmation.days') }}</dd>
          </div>
          <div>
            <dt>{{ t('restocking.confirmation.expectedDelivery') }}</dt>
            <dd>{{ formatDate(confirmation.expected_delivery) }}</dd>
          </div>
        </dl>
        <router-link to="/orders" class="confirmation-link">{{ t('restocking.confirmation.viewOrders') }}</router-link>
      </div>

      <div v-if="submitError" class="submit-error" role="alert">{{ submitError }}</div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ recommendations.length }})</h3>
          <button
            type="button"
            class="btn-primary"
            :disabled="recommendations.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="recommendations.length === 0" class="empty-state">
          {{ t('restocking.empty') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.supplier') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.item_sku">
                <td>
                  <strong>{{ translateProductName(rec.item_name) }}</strong>
                  <div class="sku">{{ rec.item_sku }}</div>
                </td>
                <td>{{ rec.supplier_name }}</td>
                <td><strong>{{ rec.quantity }}</strong></td>
                <td>{{ money(rec.unit_cost, 2) }}</td>
                <td><strong>{{ money(rec.line_cost, 2) }}</strong></td>
                <td>{{ rec.lead_time_days }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(0)
    const submitting = ref(false)
    const submitError = ref(null)
    const confirmation = ref(null)

    const money = (amount, decimals = 0) => {
      const value = Number.isFinite(amount) ? amount : 0
      return decimals > 0
        ? formatCurrencyWithDecimals(value, currentCurrency.value, decimals)
        : formatCurrency(value, currentCurrency.value)
    }

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
    }

    const items = computed(() =>
      forecasts.value
        .map(f => ({
          ...f,
          unit_cost: Number(f.unit_cost) || 0,
          shortfall: Math.max(0, (f.forecasted_demand || 0) - (f.current_demand || 0))
        }))
    )

    const fullRestockCost = computed(() =>
      items.value.reduce((sum, i) => sum + i.shortfall * i.unit_cost, 0)
    )

    const rawMax = computed(() => Math.max(1, Math.ceil(fullRestockCost.value)))
    const sliderStep = computed(() => {
      if (rawMax.value >= 10000) return 100
      if (rawMax.value >= 1000) return 10
      return 1
    })
    const sliderMax = computed(() => Math.ceil(rawMax.value / sliderStep.value) * sliderStep.value)
    const fillPercent = computed(() => (sliderMax.value > 0 ? (budget.value / sliderMax.value) * 100 : 0))

    const recommendations = computed(() => {
      const ranked = items.value
        .filter(i => i.shortfall > 0 && i.unit_cost > 0)
        .sort((a, b) => {
          const aUp = a.trend === 'increasing' ? 1 : 0
          const bUp = b.trend === 'increasing' ? 1 : 0
          if (aUp !== bUp) return bUp - aUp
          return b.shortfall - a.shortfall
        })

      let remaining = budget.value
      const result = []
      const seen = new Set()
      for (const item of ranked) {
        if (seen.has(item.item_sku)) continue
        const quantity = Math.min(item.shortfall, Math.floor(remaining / item.unit_cost))
        if (quantity <= 0) continue
        seen.add(item.item_sku)
        const lineCost = quantity * item.unit_cost
        remaining -= lineCost
        result.push({
          item_sku: item.item_sku,
          item_name: item.item_name,
          supplier_name: item.supplier_name,
          lead_time_days: item.lead_time_days,
          unit_cost: item.unit_cost,
          quantity,
          line_cost: lineCost
        })
      }
      return result
    })

    const estimatedSpend = computed(() =>
      recommendations.value.reduce((sum, r) => sum + r.line_cost, 0)
    )
    const remainingBudget = computed(() => Math.max(0, budget.value - estimatedSpend.value))

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        forecasts.value = await api.getDemandForecasts()
        const step = sliderStep.value
        budget.value = Math.round(sliderMax.value / 2 / step) * step
      } catch (err) {
        error.value = t('restocking.errors.load') + ': ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (submitting.value || recommendations.value.length === 0) return
      submitting.value = true
      submitError.value = null
      confirmation.value = null
      try {
        const payload = recommendations.value.map(r => ({
          item_sku: r.item_sku,
          quantity: r.quantity
        }))
        confirmation.value = await api.createRestockOrder(payload)
      } catch (err) {
        console.error('Restock order failed:', err)
        submitError.value = t('restocking.errors.submit')
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      budget,
      sliderMax,
      sliderStep,
      fillPercent,
      fullRestockCost,
      recommendations,
      estimatedSpend,
      remainingBudget,
      submitting,
      submitError,
      confirmation,
      money,
      formatDate,
      placeOrder,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-card {
  margin-bottom: 1.5rem;
}

.full-cost {
  font-size: 0.875rem;
  color: #64748b;
}

.slider-wrap {
  padding: 1.5rem;
}

.slider-value {
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 1rem;
}

.budget-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(to right, #3b82f6 var(--fill, 0%), #e2e8f0 var(--fill, 0%));
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #2563eb;
  border: 3px solid white;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.3);
  cursor: pointer;
}

.budget-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #2563eb;
  border: 3px solid white;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.3);
  cursor: pointer;
}

.budget-slider::-moz-range-track {
  height: 8px;
  border-radius: 4px;
  background: transparent;
}

.budget-slider:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.4);
}

.budget-slider:focus-visible::-moz-range-thumb {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.4);
}

.budget-slider:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #64748b;
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
}

.summary-card.accent {
  border-left-color: #3b82f6;
}

.summary-card.positive {
  border-left-color: #10b981;
}

.summary-label {
  font-size: 0.813rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.summary-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  margin-top: 0.25rem;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.confirmation {
  background: #ecfdf5;
  border: 1px solid #10b981;
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}

.confirmation h3 {
  margin: 0 0 1rem;
  font-size: 1.125rem;
  color: #065f46;
}

.confirmation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin: 0 0 1rem;
}

.confirmation-grid dt {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.confirmation-grid dd {
  margin: 0.25rem 0 0;
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
}

.confirmation-link {
  color: #2563eb;
  font-weight: 600;
  text-decoration: none;
}

.confirmation-link:hover {
  text-decoration: underline;
}

.submit-error {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  color: #b91c1c;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.sku {
  font-size: 0.75rem;
  color: #64748b;
}
</style>
