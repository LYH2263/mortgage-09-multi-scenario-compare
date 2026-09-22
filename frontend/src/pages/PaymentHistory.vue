<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
const loadError = ref('')
onMounted(async () => {
  try {
    const raw = (await getJSON('/api/history')).items
    // 直接渲染落库时钉住的 JSON 快照：打开即见全部套别，后续新对照不会改写
    items.value = raw.map(h => ({
      ...h,
      input: JSON.parse(h.input_json),
      result: JSON.parse(h.result_json),
    }))
  } catch (e) { loadError.value = e.message }
})
</script>
<template><div class="page">
  <h1>试算记录</h1>
  <p v-if="loadError" style="color:#b00020">加载失败：{{ loadError }}</p>
  <div v-for="h in items" :key="h.id" class="hist-card">
    <div class="hist-head">#{{ h.id }} · {{ h.kind === 'compare' ? '多方案对照' : '等额本息' }} · {{ h.created_at }}</div>
    <table v-if="h.kind === 'compare'">
      <tr><th>套号</th><th>年利率%</th><th>期数</th><th>月供</th><th>利息合计</th><th>还款合计</th><th></th></tr>
      <tr v-for="p in h.result.plans" :key="p.index">
        <td>第 {{ p.index }} 套</td>
        <td>{{ p.annual_rate }}</td>
        <td>{{ p.months }}</td>
        <td>{{ p.monthly_payment }}</td>
        <td>{{ p.total_interest }}</td>
        <td>{{ p.total_payment }}</td>
        <td><strong v-if="p.index === h.result.best_index">★ 最优</strong></td>
      </tr>
    </table>
    <p class="hist-foot" v-if="h.kind === 'compare'">
      本金 {{ h.input.principal }}；利息最小为第 {{ h.result.best_index }} 套，
      与第 {{ h.result.runner_up_index }} 套利息差 {{ h.result.interest_gap }} 元
    </p>
    <table v-else>
      <tr><th>本金</th><th>年利率%</th><th>期数</th><th>月供</th><th>利息合计</th></tr>
      <tr>
        <td>{{ h.input.principal }}</td><td>{{ h.input.annual_rate }}</td><td>{{ h.input.months }}</td>
        <td>{{ h.result.monthly_payment }}</td><td>{{ h.result.total_interest }}</td>
      </tr>
    </table>
  </div>
</div></template>
<style scoped>
.hist-card { margin: 0.75rem 0; background: var(--panel); border: 1px solid var(--grid); padding: 0.5rem; }
.hist-head { font-weight: 700; margin-bottom: 0.4rem; }
.hist-foot { margin: 0.4rem 0 0; }
</style>
