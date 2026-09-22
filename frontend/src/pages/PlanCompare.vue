<script setup>
import { computed, ref } from 'vue'
import { postJSON } from '../api'

const principal = ref(800000)
const plans = ref([
  { annual_rate: 4.2, months: 360 },
  { annual_rate: 3.5, months: 240 },
])
const out = ref(null)
const error = ref('')

const MIN_PLANS = 2
const MAX_PLANS = 3
const canAdd = computed(() => plans.value.length < MAX_PLANS)
const canRemove = computed(() => plans.value.length > MIN_PLANS)

const addPlan = () => { if (canAdd.value) plans.value.push({ annual_rate: 3.9, months: 300 }) }
const removePlan = (i) => { if (canRemove.value) plans.value.splice(i, 1) }
const fmt = (v) => Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const run = async () => {
  error.value = ''
  out.value = null
  try {
    out.value = await postJSON('/api/compare', {
      principal: principal.value,
      plans: plans.value.map(p => ({ annual_rate: p.annual_rate, months: p.months })),
      persist: true,
    })
  } catch (e) {
    error.value = e.message || String(e)
  }
}
</script>

<template>
  <div class="page">
    <h1>多方案对照</h1>
    <p>同一本金下提交 {{ MIN_PLANS }}~{{ MAX_PLANS }} 套年利率与期数组合，分别给出月供、利息合计与还款合计，并标出利息最小套。</p>
    <label>本金 <input v-model.number="principal" type="number" min="0" step="10000" /></label>

    <table style="margin-top:0.75rem">
      <thead>
        <tr><th>套号</th><th>年利率%</th><th>期数（月）</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="(p, i) in plans" :key="i">
          <td>第{{ i + 1 }}套</td>
          <td><input v-model.number="p.annual_rate" type="number" min="0" step="0.01" /></td>
          <td><input v-model.number="p.months" type="number" min="1" max="600" step="1" /></td>
          <td><button type="button" :disabled="!canRemove" @click="removePlan(i)">删除</button></td>
        </tr>
      </tbody>
    </table>
    <div style="margin:0.6rem 0; display:flex; gap:0.5rem; align-items:center">
      <button type="button" :disabled="!canAdd" @click="addPlan">增加一套</button>
      <button type="button" @click="run">开始对照</button>
      <span style="color:#a33" v-if="error">整单失败：{{ error }}</span>
    </div>

    <template v-if="out">
      <table>
        <thead>
          <tr><th>套号</th><th>年利率%</th><th>期数</th><th>月供</th><th>利息合计</th><th>还款合计</th><th>标记</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in out.plans" :key="p.plan_index" :style="p.plan_index === out.best_index ? 'background:#f3e6c8;font-weight:700' : ''">
            <td>第{{ p.plan_index }}套</td>
            <td>{{ p.annual_rate }}</td>
            <td>{{ p.months }}</td>
            <td>{{ fmt(p.monthly_payment) }}</td>
            <td>{{ fmt(p.total_interest) }}</td>
            <td>{{ fmt(p.total_payment) }}</td>
            <td>
              <span v-if="p.plan_index === out.best_index">★ 利息最小（最优）</span>
              <span v-else-if="p.plan_index === out.runner_up_index">次小</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top:0.6rem">
        最优：<strong>第{{ out.best_index }}套</strong>，
        比第{{ out.runner_up_index }}套少还利息 <strong>{{ fmt(out.interest_gap) }}</strong> 元
        （记录 #{{ out.run_id }}）。
      </p>
    </template>
  </div>
</template>
