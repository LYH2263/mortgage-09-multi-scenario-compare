<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
const fmt = (v) => Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const parse = (s) => { try { return JSON.parse(s) } catch { return null } }

onMounted(async () => {
  const raw = (await getJSON('/api/history')).items
  items.value = raw.map(h => ({ ...h, inp: parse(h.input_json), res: parse(h.result_json) }))
})
</script>
<template><div class="page">
  <h1>试算记录</h1>
  <div v-for="h in items" :key="h.id" style="margin-bottom:1rem; border:1px solid var(--grid); background:var(--panel)">
    <div style="padding:0.4rem 0.6rem; background:#ebe3d4">
      #{{ h.id }} · {{ h.kind === 'compare' ? '多方案对照' : '等额本息' }} · {{ h.created_at }}
    </div>
    <!-- 对照记录：一次看到全部套别；内容取自落库快照，不被后续新对照改写 -->
    <template v-if="h.kind === 'compare'">
      <table>
        <thead>
          <tr><th>套号</th><th>年利率%</th><th>期数</th><th>月供</th><th>利息合计</th><th>还款合计</th><th>标记</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in h.res?.plans || []" :key="p.plan_index"
              :style="p.plan_index === h.res.best_index ? 'background:#f3e6c8;font-weight:700' : ''">
            <td>第{{ p.plan_index }}套</td>
            <td>{{ p.annual_rate }}</td>
            <td>{{ p.months }}</td>
            <td>{{ fmt(p.monthly_payment) }}</td>
            <td>{{ fmt(p.total_interest) }}</td>
            <td>{{ fmt(p.total_payment) }}</td>
            <td>
              <span v-if="p.plan_index === h.res.best_index">★ 最优</span>
              <span v-else-if="p.plan_index === h.res.runner_up_index">次小</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div style="padding:0.4rem 0.6rem">
        本金 {{ fmt(h.inp?.principal) }} · 共 {{ h.res?.plans?.length }} 套 ·
        最优 <strong>第{{ h.res?.best_index }}套</strong>，与次小利息差 {{ fmt(h.res?.interest_gap) }}
      </div>
    </template>
    <table v-else>
      <tr><td>月供</td><td>{{ h.res?.monthly_payment }}</td>
          <td>利息合计</td><td>{{ h.res?.total_interest }}</td></tr>
    </table>
  </div>
</div></template>
