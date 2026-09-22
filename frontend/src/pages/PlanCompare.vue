<script setup>
import { ref } from 'vue'
import { postJSON } from '../api'
const principal = ref(800000)
const plans = ref([
  { annual_rate: 3.5, months: 360 },
  { annual_rate: 4.2, months: 240 },
])
const out = ref(null)
const err = ref('')
const addPlan = () => { if (plans.value.length < 3) plans.value.push({ annual_rate: 3.1, months: 300 }) }
const removePlan = (i) => { if (plans.value.length > 2) plans.value.splice(i, 1) }
const run = async () => {
  err.value = ''
  out.value = null
  try {
    out.value = await postJSON('/api/compare', {
      principal: principal.value,
      plans: plans.value.map(p => ({ annual_rate: p.annual_rate, months: p.months })),
      persist: true,
    })
  } catch (e) {
    try { err.value = JSON.parse(e.message).detail ?? e.message } catch { err.value = e.message }
  }
}
</script>
<template><div class="page">
  <h1>多方案对照</h1>
  <label>本金 <input v-model.number="principal" /></label>
  <h2>方案（2~3 套）</h2>
  <table>
    <tr><th>套号</th><th>年利率%</th><th>期数（月）</th><th></th></tr>
    <tr v-for="(p, i) in plans" :key="i">
      <td>第 {{ i + 1 }} 套</td>
      <td><input v-model.number="p.annual_rate" /></td>
      <td><input v-model.number="p.months" /></td>
      <td><button :disabled="plans.length <= 2" @click="removePlan(i)">删除</button></td>
    </tr>
  </table>
  <p>
    <button :disabled="plans.length >= 3" @click="addPlan">增加一套</button>
    <button @click="run">对照试算</button>
  </p>
  <p v-if="err" style="color:#b00020">试算失败：{{ err }}</p>
  <template v-if="out">
    <h2>结果（本金 {{ out.principal }}）</h2>
    <table>
      <tr><th>套号</th><th>年利率%</th><th>期数</th><th>月供</th><th>利息合计</th><th>还款合计</th><th></th></tr>
      <tr v-for="p in out.plans" :key="p.index">
        <td>第 {{ p.index }} 套</td>
        <td>{{ p.annual_rate }}</td>
        <td>{{ p.months }}</td>
        <td>{{ p.monthly_payment }}</td>
        <td>{{ p.total_interest }}</td>
        <td>{{ p.total_payment }}</td>
        <td><strong v-if="p.index === out.best_index">★ 最优</strong></td>
      </tr>
    </table>
    <p>利息最小为第 <strong>{{ out.best_index }}</strong> 套，与第 {{ out.runner_up_index }} 套的利息差为 <strong>{{ out.interest_gap }}</strong> 元。</p>
    <p v-if="out.run_id">已保存对照记录 #{{ out.run_id }}（单条快照，可在记录页查看）。</p>
  </template>
</div></template>
