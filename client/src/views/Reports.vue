<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('reports.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="!hasData" class="loading">{{ t('reports.noData') }}</div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterly.title') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.quarterly.quarter') }}</th>
                <th>{{ t('reports.quarterly.totalOrders') }}</th>
                <th>{{ t('reports.quarterly.totalRevenue') }}</th>
                <th>{{ t('reports.quarterly.avgOrderValue') }}</th>
                <th>{{ t('reports.quarterly.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ q.quarter }}</strong></td>
                <td>{{ formatInteger(q.total_orders) }}</td>
                <td>{{ formatCurrency(q.total_revenue) }}</td>
                <td>{{ formatCurrency(q.avg_order_value) }}</td>
                <td>
                  <span :class="getFulfillmentClass(q.fulfillment_rate)">
                    {{ formatPercent(q.fulfillment_rate) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.trend.title') }}</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div v-for="month in monthlyData" :key="month.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: getBarHeight(month.revenue) + 'px' }"
                  :title="formatCurrency(month.revenue)"
                ></div>
              </div>
              <div class="bar-label">{{ formatMonth(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.mom.title') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.mom.month') }}</th>
                <th>{{ t('reports.mom.orders') }}</th>
                <th>{{ t('reports.mom.revenue') }}</th>
                <th>{{ t('reports.mom.change') }}</th>
                <th>{{ t('reports.mom.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(month, index) in monthlyData" :key="month.month">
                <td><strong>{{ formatMonth(month.month) }}</strong></td>
                <td>{{ formatInteger(month.order_count) }}</td>
                <td>{{ formatCurrency(month.revenue) }}</td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getChangeValue(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getGrowthRate(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(totalRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalOrders') }}</div>
          <div class="stat-value">{{ formatInteger(totalOrders) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'

// Coerce possibly missing/invalid API values to a finite number
const toNumber = (value) => {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

export default {
  name: 'Reports',
  setup() {
    const { t, currentLocale, currentCurrency } = useI18n()

    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const quarterlyRaw = ref([])
    const monthlyRaw = ref([])

    const currencySymbol = computed(() => (currentCurrency.value === 'JPY' ? '¥' : '$'))
    const numberLocale = computed(() => (currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'))

    // Month-over-month comparisons assume chronological order; YYYY-MM sorts lexically
    const monthlyData = computed(() =>
      [...monthlyRaw.value].sort((a, b) => String(a.month).localeCompare(String(b.month)))
    )
    const quarterlyData = computed(() => quarterlyRaw.value)

    const hasData = computed(() => quarterlyData.value.length > 0 || monthlyData.value.length > 0)

    // Summary stats derived from the (already filtered) data
    const totalRevenue = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + toNumber(m.revenue), 0)
    )
    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length > 0 ? totalRevenue.value / monthlyData.value.length : 0
    )
    const totalOrders = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + toNumber(m.order_count), 0)
    )
    const bestQuarter = computed(() => {
      let best = null
      for (const q of quarterlyData.value) {
        if (best === null || toNumber(q.total_revenue) > toNumber(best.total_revenue)) best = q
      }
      return best && toNumber(best.total_revenue) > 0 ? best.quarter : '-'
    })

    // Computed once instead of per bar
    const maxRevenue = computed(() =>
      monthlyData.value.reduce((max, m) => Math.max(max, toNumber(m.revenue)), 0)
    )

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])
        quarterlyRaw.value = Array.isArray(quarterly) ? quarterly : []
        monthlyRaw.value = Array.isArray(monthly) ? monthly : []
      } catch (err) {
        error.value = t('reports.loadError')
        console.error('Failed to load reports:', err)
      } finally {
        loading.value = false
      }
    }

    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadData()
    })

    onMounted(() => {
      loadData()
    })

    const formatCurrency = (value) => {
      return currencySymbol.value + toNumber(value).toLocaleString(numberLocale.value, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    }

    const formatInteger = (value) => toNumber(value).toLocaleString(numberLocale.value)

    const formatPercent = (value) => {
      if (value === null || value === undefined || !Number.isFinite(Number(value))) return '-'
      return `${Number(value)}%`
    }

    // Convert 'YYYY-MM' to a localized short month + year; fall back to the raw value if invalid
    const formatMonth = (monthStr) => {
      if (typeof monthStr !== 'string') return '-'
      const date = new Date(`${monthStr}-01T00:00:00`)
      if (isNaN(date.getTime())) return monthStr
      return date.toLocaleDateString(numberLocale.value, { year: 'numeric', month: 'short' })
    }

    // Scale bars to a 200px max height
    const getBarHeight = (revenue) => {
      if (maxRevenue.value === 0) return 0
      return (toNumber(revenue) / maxRevenue.value) * 200
    }

    const getFulfillmentClass = (rate) => {
      const n = Number(rate)
      if (rate === null || rate === undefined || !Number.isFinite(n)) return 'badge info'
      if (n >= 90) return 'badge success'
      if (n >= 75) return 'badge warning'
      return 'badge danger'
    }

    const getChangeValue = (current, previous) => {
      const change = toNumber(current) - toNumber(previous)
      if (change > 0) return '+' + formatCurrency(change)
      if (change < 0) return '-' + formatCurrency(Math.abs(change))
      return formatCurrency(0)
    }

    const getChangeClass = (current, previous) => {
      const change = toNumber(current) - toNumber(previous)
      if (change > 0) return 'positive-change'
      if (change < 0) return 'negative-change'
      return ''
    }

    const getGrowthRate = (current, previous) => {
      const prev = toNumber(previous)
      // Growth from a zero base is undefined
      if (prev === 0) return '-'
      const rate = ((toNumber(current) - prev) / prev) * 100
      return (rate > 0 ? '+' : '') + rate.toFixed(1) + '%'
    }

    return {
      t,
      loading,
      error,
      hasData,
      quarterlyData,
      monthlyData,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      formatCurrency,
      formatInteger,
      formatPercent,
      formatMonth,
      getBarHeight,
      getFulfillmentClass,
      getChangeValue,
      getChangeClass,
      getGrowthRate
    }
  }
}
</script>

<style scoped>
/* Shared .card, .stats-grid, .stat-card, .badge, .loading, .error styles come from App.vue */
.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  background: #f8fafc;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #64748b;
  border-bottom: 2px solid #e2e8f0;
}

.reports-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}

.reports-table tr:hover {
  background: #f8fafc;
}

.chart-container {
  padding: 2rem 1rem;
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: 0.5rem;
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: linear-gradient(to top, #3b82f6, #60a5fa);
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, #2563eb, #3b82f6);
}

.bar-label {
  font-size: 0.75rem;
  color: #64748b;
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: 1.5rem;
}

.positive-change {
  color: #16a34a;
  font-weight: 600;
}

.negative-change {
  color: #dc2626;
  font-weight: 600;
}
</style>
