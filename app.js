/* SRNHS School Profile Analysis Dashboard - interactive client UI */
const $ = id => document.getElementById(id);
const $$ = selector => Array.from(document.querySelectorAll(selector));
const gradeLabels = ['Grade 7','Grade 8','Grade 9','Grade 10','Grade 11','Grade 12'];
const chartColors = {
  deep:'#0B3D24', dark:'#0F633B', green:'#168447', mid:'#2B9960', accent:'#58B878', sage:'#85C99B',
  light:'#CDEBD5', mint:'#E5F4EA', pale:'#F4FBF6', warning:'#E5B43E', danger:'#B84B53', white:'#FFFFFF'
};
const state = {data:null, charts:{}, years:[], selectedYears:[], allYears:true, level:'All', forecast:true, activityType:'All'};

Chart.defaults.font.family = 'Poppins, Arial, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = '#52665A';
Chart.defaults.plugins.legend.labels.font = {size:12, weight:'600'};
Chart.defaults.plugins.legend.labels.boxWidth = 14;
Chart.defaults.plugins.legend.labels.padding = 12;
Chart.defaults.plugins.tooltip.titleFont = {size:13, weight:'700'};
Chart.defaults.plugins.tooltip.bodyFont = {size:12};
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.backgroundColor = '#071B12';
Chart.defaults.plugins.tooltip.cornerRadius = 14;

function fmt(value, decimals=0){ if(value===null || value===undefined || value==='') return '—'; return Number(value).toLocaleString(undefined,{minimumFractionDigits:decimals,maximumFractionDigits:decimals}); }
function percent(value){ return value===null || value===undefined ? '—' : `${Number(value).toFixed(2)}%`; }
function initials(name){ return (name||'SR').split(/\s+/).slice(0,2).map(s=>s[0]).join('').toUpperCase(); }
function esc(v){ return String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function avatarMarkup(account, cls='avatar'){ return account.avatar_url ? `<span class="${cls}"><img src="${esc(account.avatar_url)}" alt="${esc(account.full_name)}"></span>` : `<span class="${cls}">${initials(account.full_name)}</span>`; }
function toast(message,error=false){ const node=$('toast'); node.textContent=message; node.classList.toggle('error',error); node.classList.add('show'); clearTimeout(toast.timer); toast.timer=setTimeout(()=>node.classList.remove('show'),4200); }
function modal(id,open=true){ $(id)?.classList.toggle('open',open); }
function csrf(){ return window.SRNHS.csrf; }
async function api(url, options={}){
  const cfg={...options,headers:{...(options.headers||{})}};
  if(cfg.method && cfg.method !== 'GET') cfg.headers['X-CSRF-Token']=csrf();
  if(cfg.body && !(cfg.body instanceof FormData)) cfg.headers['Content-Type']='application/json';
  const response=await fetch(url,cfg); const result=await response.json().catch(()=>({}));
  if(!response.ok) throw new Error(result.error||'Request failed.'); return result;
}
function destroyChart(id){ if(state.charts[id]){state.charts[id].destroy(); delete state.charts[id];} }
function canvasGradient(ctx, top, bottom){ const gradient=ctx.createLinearGradient(0,0,0,350); gradient.addColorStop(0,top); gradient.addColorStop(1,bottom); return gradient; }
function chartOptions({percentAxis=false, indexMode=true, stacked=false, horizontal=false, forecastLegend=false}={}){
  return {responsive:true, maintainAspectRatio:false, interaction:{mode:indexMode?'index':'nearest',intersect:false},
    animation:{duration:700}, plugins:{legend:{display:true,position:'bottom',labels:{usePointStyle:true,padding:12,font:{size:12,weight:'600'}},onClick:forecastLegend?(event,item,legend)=>{
      const chart=legend.chart;
      if(item.text==='Projected Enrollment'){
        const panel=chart.canvas.closest('.chart-panel');
        if(panel){
          panel.classList.toggle('forecast-expanded');
          panel.scrollIntoView({behavior:'smooth',block:'nearest'});
          setTimeout(()=>chart.resize(),220);
        }
        return;
      }
      const meta=chart.getDatasetMeta(item.datasetIndex);
      meta.hidden=meta.hidden===null ? !chart.data.datasets[item.datasetIndex].hidden : !meta.hidden;
      chart.update();
    }:undefined}, tooltip:{enabled:true,callbacks:{label(ctx){ const raw=ctx.raw===null?'—':Number(ctx.raw); return ` ${ctx.dataset.label}: ${percentAxis && raw!==null ? raw.toFixed(2)+'%' : fmt(raw, Number.isInteger(raw)?0:1)}`; }}}},
    scales:{x:{stacked,ticks:{font:{size:12,weight:'600'},color:'#52665A'},grid:{display:false}}, y:{stacked,beginAtZero:true,ticks:{font:{size:12,weight:'600'},color:'#52665A',callback:v=>percentAxis?`${v}%`:fmt(v)},grid:{color:'rgba(11,61,36,.08)'}}}, indexAxis:horizontal?'y':'x'};
}
function enrollmentTrendData(ctx, rows, forecasts){
  const labels=rows.map(r=>r.school_year), actual=rows.map(r=>r.enrollment), datasets=[lineDataset(ctx,'Actual Enrollment',actual,chartColors.green,true)];
  if(state.forecast){
    const expanded=[...labels,...forecasts.map(r=>r.school_year)];
    const actualExtended=[...actual,...forecasts.map(()=>null)];
    const projected=[...rows.map(()=>null),...forecasts.map(r=>r.enrollment)];
    if(rows.length && forecasts.length) projected[rows.length-1]=rows[rows.length-1].enrollment;
    return {labels:expanded,datasets:[lineDataset(ctx,'Actual Enrollment',actualExtended,chartColors.green,true),lineDataset(ctx,'Projected Enrollment',projected,chartColors.dark,false)]};
  }
  return {labels,datasets};
}
function makeChart(id,type,data,options){ destroyChart(id); const canvas=$(id); if(!canvas)return; state.charts[id]=new Chart(canvas,{type,data,options}); }
function lineDataset(ctx,label,data,color,fill=false){ return {label,data,borderColor:color,backgroundColor:fill?canvasGradient(ctx,`${color}55`,`${color}05`):color,borderWidth:3.2,pointRadius:5,pointHoverRadius:8,pointBackgroundColor:'#fff',pointBorderColor:color,pointBorderWidth:2,tension:.32,fill}; }
function barDataset(ctx,label,data,top,bottom){ return {label,data,backgroundColor:canvasGradient(ctx,top,bottom),borderColor:top,borderWidth:1,borderRadius:10,borderSkipped:false}; }

async function refreshData(initial=false){
  const params=new URLSearchParams(); if(!state.allYears && state.selectedYears.length) params.set('years',state.selectedYears.join(',')); params.set('level',state.level);
  const response=await api(`/api/dashboard?${params}`); state.data=response;
  if(initial){ state.years=response.analytics.years; state.selectedYears=[...state.years]; state.allYears=true; }
  else { state.years=response.analytics.years; if(state.allYears) state.selectedYears=[...state.years]; }
  renderEverything();
}

function bindNavigation(){
  $$('[data-page]').forEach(btn=>btn.onclick=()=>showPage(btn.dataset.page));
  $$('[data-page-link]').forEach(btn=>btn.onclick=()=>{showPage(btn.dataset.pageLink); if(btn.dataset.insightTab) activateTab('insights',btn.dataset.insightTab);});
  $('menuToggle').onclick=()=>$('sidebar').classList.toggle('open');
  document.addEventListener('click', e=>{if(!$('profileToggle').contains(e.target) && !$('profileMenu').contains(e.target)) $('profileMenu').classList.remove('open');});
  $$('.tab-row').forEach(row=>row.querySelectorAll('.tab').forEach(tab=>tab.onclick=()=>activateTab(row.dataset.tabGroup,tab.dataset.tab)));
}
function showPage(page){ $$('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page)); $$('.app-page').forEach(p=>p.classList.toggle('active',p.id===`page-${page}`)); $('pageTitle').textContent=({dashboard:'Dashboard',analytics:'Analytics',insights:'Insights & Actions',records:'School Records',reports:'Reports',accounts:'Accounts'})[page]||'Dashboard'; $('sidebar').classList.remove('open'); }
function activateTab(group,tab){ const root=document.querySelector(`[data-tab-group="${group}"]`); if(!root)return; root.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab)); const prefix={analytics:'analytics',insights:'insights',records:'records',accounts:'accounts'}[group]; document.querySelectorAll(`[id^="${prefix}-"]`).forEach(panel=>panel.classList.toggle('active',panel.id===`${prefix}-${tab}`)); }
function bindFilters(){
  $('allYearsButton').onclick=()=>{state.allYears=true;state.selectedYears=[...state.years];refreshData();};
  $('forecastToggle').onclick=()=>{state.forecast=!state.forecast;$('forecastToggle').classList.toggle('active',state.forecast);$('forecastToggle').textContent=state.forecast?'Forecast On':'Forecast Off';renderCharts();renderForecast();};
  $('resetFilters').onclick=()=>{state.allYears=true;state.selectedYears=[...state.years];state.level='All';state.forecast=true;$('forecastToggle').classList.add('active');$('forecastToggle').textContent='Forecast On';$$('#levelToggle button').forEach(b=>b.classList.toggle('selected',b.dataset.segment==='All'));refreshData();};
  $$('#levelToggle button').forEach(btn=>btn.onclick=()=>{state.level=btn.dataset.segment;$$('#levelToggle button').forEach(b=>b.classList.toggle('selected',b===btn));refreshData();});
}
function renderYearPills(){
  $('allYearsButton').classList.toggle('selected',state.allYears);
  $('yearPills').innerHTML=state.years.map(year=>`<button class="year-pill ${!state.allYears&&state.selectedYears.includes(year)?'selected':''}" data-year="${year}">${year}</button>`).join('');
  $$('#yearPills .year-pill').forEach(btn=>btn.onclick=()=>{state.allYears=false;const year=btn.dataset.year;state.selectedYears.includes(year)?state.selectedYears=state.selectedYears.filter(y=>y!==year):state.selectedYears.push(year);if(!state.selectedYears.length){state.allYears=true;state.selectedYears=[...state.years];}state.selectedYears.sort();refreshData();});
  $('viewCaption').textContent=state.data.analytics.selection_caption + (state.level==='All'?'':' · '+state.level);
}

function kpiValue(k){ if(k.value===null||k.value===undefined)return '—'; if(k.suffix==='%')return percent(k.value); if(k.suffix===':1')return `${fmt(k.value,1)}:1`; return `${fmt(k.value)} <small>${k.suffix}</small>`; }
function renderKpiDetail(k){
  if(!k || !$('kpiDetailPanel')) return;
  const h=k.hover_summary || {
    what:'No explanation is currently available.',
    why:'Review the saved school records.',
    next:'Monitor future uploaded data.',
    action:'Continue annual data review.'
  };
  $('kpiDetailPanel').innerHTML=`
    <div class="kpi-detail-content">
      <div class="kpi-detail-title">
        <span class="kpi-detail-tag">KPI Analysis</span>
        <h3>${esc(k.label)}</h3>
        <div class="kpi-detail-value">${kpiValue(k)}</div>
        <p>${esc(k.comparison_label || 'Selected view')}</p>
      </div>
      <div class="kpi-detail-grid">
        <article class="kpi-answer what"><h4>What happened?</h4><p>${esc(h.what)}</p></article>
        <article class="kpi-answer why"><h4>Why review it?</h4><p>${esc(h.why)}</p></article>
        <article class="kpi-answer next"><h4>What may happen?</h4><p>${esc(h.next)}</p></article>
        <article class="kpi-answer action"><h4>What should be done?</h4><p>${esc(h.action)}</p></article>
      </div>
    </div>`;
}
function renderKpis(){
  const icons=['◎','↘','↻','◌','♟','⇄'];
  const entries=Object.values(state.data.analytics.kpis);
  $('kpiGrid').innerHTML=entries.map((k,i)=>{
    const delta=k.change_pp!==null&&k.change_pp!==undefined ? `${k.change_pp>0?'+':''}${k.change_pp.toFixed(2)} pp` : k.change!==null&&k.change!==undefined ? `${k.change>0?'+':''}${fmt(k.change,Math.abs(k.change)%1?1:0)}${k.change_pct!==null&&k.change_pct!==undefined?` (${k.change_pct>0?'+':''}${k.change_pct.toFixed(2)}%)`:''}` : 'Selected view';
    const negative=(k.label==='Total Enrollment'&&k.change<0)||(['Dropout Rate','Repeater Rate'].includes(k.label)&&k.change_pp>0)||(['Cohort Survival','Transition Rate'].includes(k.label)&&k.change_pp<0);
    return `<article class="kpi-card ${i===0?'detail-selected':''}" tabindex="0" data-kpi-index="${i}" aria-label="Show ${esc(k.label)} explanation"><div class="kpi-top"><span class="kpi-icon">${icons[i]}</span><span>${esc(k.label)}</span></div><div class="kpi-change ${negative?'negative':''}">${esc(delta)} · ${esc(k.comparison_label)}</div><div class="kpi-value">${kpiValue(k)}</div></article>`;
  }).join('');
  const cards=$$('#kpiGrid .kpi-card');
  function selectCard(card,index){
    cards.forEach(item=>item.classList.remove('detail-selected'));
    card.classList.add('detail-selected');
    renderKpiDetail(entries[index]);
  }
  cards.forEach((card,index)=>{
    card.addEventListener('mouseenter',()=>selectCard(card,index));
    card.addEventListener('focus',()=>selectCard(card,index));
    card.addEventListener('click',()=>selectCard(card,index));
  });
  const defaultIndex=Math.max(0,entries.findIndex(k=>k.label==='Total Enrollment'));
  if(entries[defaultIndex]){
    cards.forEach(item=>item.classList.remove('detail-selected'));
    if(cards[defaultIndex]) cards[defaultIndex].classList.add('detail-selected');
    renderKpiDetail(entries[defaultIndex]);
  }
}

function chosenSummary(){ return state.data.analytics.summary; }
function latestRecords(){ const year=state.data.analytics.latest.school_year; return state.data.records.filter(r=>r.school_year===year && (state.level==='All' || r.level===state.level)); }
function selectedPeriodRecords(){
  const selected=new Set(state.data.analytics.selected_years);
  return gradeLabels.map(grade=>{
    const rows=state.data.records.filter(r=>selected.has(r.school_year) && r.grade_level===grade && (state.level==='All' || r.level===state.level));
    if(!rows.length) return null;
    return {grade_level:grade,enrollment:rows.reduce((sum,r)=>sum+Number(r.enrollment||0),0),repeaters:rows.reduce((sum,r)=>sum+Number(r.repeaters||0),0),dropouts:rows.reduce((sum,r)=>sum+Number(r.dropouts||0),0)};
  }).filter(Boolean);
}
function renderCharts(){
  const a=state.data.analytics, rows=chosenSummary(), labels=rows.map(r=>r.school_year), selectedRows=selectedPeriodRecords(), selectedPeriod=a.selected_years.length>1 ? 'Selected-period total' : a.selected_years[0];
  // Enrollment trend expands into projected years only while forecast is visible. Clicking the Projected legend toggles that expansion.
  let ctx=$('enrollmentChart')?.getContext('2d'); if(ctx) makeChart('enrollmentChart','line',enrollmentTrendData(ctx, rows, a.forecast),chartOptions({forecastLegend:true}));
  ctx=$('levelCompositionChart')?.getContext('2d'); if(ctx) makeChart('levelCompositionChart','bar',{labels,datasets:[barDataset(ctx,'JHS',rows.map(r=>r.jhs),'#168447','#85C99B'),barDataset(ctx,'SHS',rows.map(r=>r.shs),'#0B3D24','#58B878')]},chartOptions({stacked:true}));
  ctx=$('gradeChart')?.getContext('2d'); if(ctx) makeChart('gradeChart','bar',{labels:selectedRows.map(r=>r.grade_level),datasets:[barDataset(ctx,`Enrollment · ${selectedPeriod}`,selectedRows.map(r=>r.enrollment),'#168447','#CDEBD5')]},chartOptions({horizontal:true,indexMode:false}));
  ctx=$('retentionChart')?.getContext('2d'); if(ctx) makeChart('retentionChart','bar',{labels,datasets:[barDataset(ctx,'Dropouts',rows.map(r=>r.dropouts),'#E5B43E','#FFF6DC'),barDataset(ctx,'Repeaters',rows.map(r=>r.repeaters),'#0F633B','#85C99B')]},chartOptions());
  ctx=$('continuityChart')?.getContext('2d'); if(ctx) makeChart('continuityChart','line',{labels,datasets:[lineDataset(ctx,'Cohort Survival %',rows.map(r=>r.cohort_survival),chartColors.green,true),lineDataset(ctx,'Transition Rate %',rows.map(r=>r.transition_rate),chartColors.dark,false)]},chartOptions({percentAxis:true}));
  ctx=$('ratioChart')?.getContext('2d'); if(ctx) makeChart('ratioChart','line',{labels,datasets:[lineDataset(ctx,'Students / Teacher',rows.map(r=>r.student_teacher_ratio),chartColors.green,true),lineDataset(ctx,'Students / Classroom',rows.map(r=>r.students_per_classroom),chartColors.dark,false)]},chartOptions());
  ctx=$('changeChart')?.getContext('2d'); if(ctx) makeChart('changeChart','bar',{labels,datasets:[barDataset(ctx,'Enrollment Change',rows.map(r=>r.enrollment_change),'#58B878','#D1EED9')]},chartOptions());
  ctx=$('repeaterShareChart')?.getContext('2d'); if(ctx){ destroyChart('repeaterShareChart'); state.charts.repeaterShareChart=new Chart(ctx,{type:'doughnut',data:{labels:selectedRows.map(r=>r.grade_level),datasets:[{label:'Repeaters · '+selectedPeriod,data:selectedRows.map(r=>r.repeaters),backgroundColor:['#0B3D24','#0F633B','#168447','#2B9960','#58B878','#A7D9B5'],borderWidth:2,borderColor:'#FFFFFF'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:true,position:'bottom',labels:{font:{size:15,weight:'600'},padding:17,usePointStyle:true}},tooltip:{callbacks:{label:c=>` ${c.label}: ${c.raw} repeaters`}}}}}); }
  renderAnalyticsCharts(); renderForecast();
}
function renderAnalyticsCharts(){
  const a=state.data.analytics, rows=a.summary, labels=rows.map(r=>r.school_year), selectedRows=selectedPeriodRecords(), selectedPeriod=a.selected_years.length>1 ? 'Selected-period total' : a.selected_years[0]; let ctx;
  ctx=$('analyticsEnrollment')?.getContext('2d'); if(ctx) makeChart('analyticsEnrollment','line',{labels,datasets:[lineDataset(ctx,'Total Enrollment',rows.map(r=>r.enrollment),chartColors.green,true)]},chartOptions());
  ctx=$('analyticsLevels')?.getContext('2d'); if(ctx) makeChart('analyticsLevels','bar',{labels,datasets:[barDataset(ctx,'JHS',rows.map(r=>r.jhs),'#168447','#A7D9B5'),barDataset(ctx,'SHS',rows.map(r=>r.shs),'#0B3D24','#58B878')]},chartOptions({stacked:true}));
  ctx=$('analyticsGrade')?.getContext('2d'); if(ctx) makeChart('analyticsGrade','bar',{labels:selectedRows.map(r=>r.grade_level),datasets:[barDataset(ctx,`Enrollment · ${selectedPeriod}`,selectedRows.map(r=>r.enrollment),'#2B9960','#CDEBD5')]},chartOptions({horizontal:true,indexMode:false}));
  ctx=$('dropoutBarChart')?.getContext('2d'); if(ctx) makeChart('dropoutBarChart','bar',{labels,datasets:[barDataset(ctx,'Dropouts',rows.map(r=>r.dropouts),'#E5B43E','#FFF6DC')]},chartOptions());
  ctx=$('repeaterBarChart')?.getContext('2d'); if(ctx) makeChart('repeaterBarChart','bar',{labels,datasets:[barDataset(ctx,'Repeaters',rows.map(r=>r.repeaters),'#0F633B','#85C99B')]},chartOptions());
  ctx=$('dropoutRateChart')?.getContext('2d'); if(ctx) makeChart('dropoutRateChart','line',{labels,datasets:[lineDataset(ctx,'Dropout Rate %',rows.map(r=>r.dropout_rate),chartColors.warning,true)]},chartOptions({percentAxis:true}));
  ctx=$('gradeRiskChart')?.getContext('2d'); if(ctx){ destroyChart('gradeRiskChart'); state.charts.gradeRiskChart=new Chart(ctx,{type:'pie',data:{labels:selectedRows.map(r=>r.grade_level),datasets:[{label:'Repeaters · '+selectedPeriod,data:selectedRows.map(r=>r.repeaters),backgroundColor:['#0B3D24','#0F633B','#168447','#2B9960','#58B878','#CDEBD5'],borderColor:'#fff',borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:true,position:'bottom',labels:{font:{size:15,weight:'600'},padding:16,usePointStyle:true}},tooltip:{callbacks:{label:c=>` ${c.label}: ${c.raw} repeaters`}}}}}); }
  ctx=$('cohortChart')?.getContext('2d'); if(ctx) makeChart('cohortChart','line',{labels,datasets:[lineDataset(ctx,'Cohort Survival %',rows.map(r=>r.cohort_survival),chartColors.green,true)]},chartOptions({percentAxis:true}));
  ctx=$('transitionChart')?.getContext('2d'); if(ctx) makeChart('transitionChart','line',{labels,datasets:[lineDataset(ctx,'Transition Rate %',rows.map(r=>r.transition_rate),chartColors.dark,true)]},chartOptions({percentAxis:true}));
  ctx=$('transitionGapChart')?.getContext('2d'); if(ctx) makeChart('transitionGapChart','bar',{labels,datasets:[barDataset(ctx,'Count Gap',rows.map(r=>r.transition_count_gap),'#168447','#A7D9B5')]},chartOptions());
  ctx=$('teacherCountChart')?.getContext('2d'); if(ctx) makeChart('teacherCountChart','bar',{labels,datasets:[barDataset(ctx,'Teachers',rows.map(r=>r.teachers),'#0F633B','#85C99B')]},chartOptions());
  ctx=$('teacherRatioChart')?.getContext('2d'); if(ctx) makeChart('teacherRatioChart','line',{labels,datasets:[lineDataset(ctx,'Students / Teacher',rows.map(r=>r.student_teacher_ratio),chartColors.green,true)]},chartOptions());
  ctx=$('classroomCountChart')?.getContext('2d'); if(ctx) makeChart('classroomCountChart','bar',{labels,datasets:[barDataset(ctx,'Total Classrooms',rows.map(r=>r.classrooms),'#0B3D24','#A7D9B5')]},chartOptions());
  ctx=$('classroomRatioChart')?.getContext('2d'); if(ctx) makeChart('classroomRatioChart','line',{labels,datasets:[lineDataset(ctx,'Students / Classroom',rows.map(r=>r.students_per_classroom),chartColors.green,true)]},chartOptions());
  const resMap=Object.fromEntries(state.data.resources.map(r=>[r.school_year,r]));
  ctx=$('roomLevelChart')?.getContext('2d'); if(ctx) makeChart('roomLevelChart','bar',{labels,datasets:[barDataset(ctx,'JHS Rooms',labels.map(y=>resMap[y]?.jhs_classrooms||0),'#168447','#A7D9B5'),barDataset(ctx,'SHS Rooms',labels.map(y=>resMap[y]?.shs_classrooms||0),'#0B3D24','#58B878')]},chartOptions({stacked:true}));
}

function renderIntelligence(){
  const a=state.data.analytics;
  $('quickInsights').innerHTML=a.insights.slice(0,6).map(i=>`<div class="bi-item"><strong>${esc(i.category)}</strong><h4>${esc(i.title)}</h4><p>${esc(i.text)}</p></div>`).join('');
  $('quickConcerns').innerHTML=a.concerns.map(c=>`<div class="bi-item"><strong>${esc(c.level)}</strong><h4>${esc(c.title)}</h4><p>${esc(c.text)}</p></div>`).join('')||'<div class="bi-item"><h4>No major concern generated</h4><p>Continue yearly monitoring as new records are saved.</p></div>';
  $('quickActions').innerHTML=a.suggested_actions.slice(0,4).map(item=>`<div class="bi-item"><h4>${esc(item.title)}</h4><p>${esc(item.action)}</p></div>`).join('');
  $('fullHighlights').innerHTML=a.insights.map(item=>`<article class="highlight-card"><span>${esc(item.category)}</span><h3>${esc(item.title)}</h3><p>${esc(item.text)}</p></article>`).join('');
  $('concernCards').innerHTML=a.concerns.map(c=>`<article class="concern-card ${c.level==='High'?'high':''}"><span class="concern-level">${esc(c.level)}</span><h3>${esc(c.title)}</h3><p>${esc(c.text)}</p></article>`).join('');
  Object.keys(a.bi_tabs).forEach(tab=>renderBIFramework(tab,a.bi_tabs[tab]));
}
function renderBIFramework(tab, values){
  const questions={descriptive:'What happened?',diagnostic:'Why might it have happened?',predictive:'What may happen next?',prescriptive:'What should be done?'};
  const node=$(`bi-${tab}`); if(!node)return;
  node.innerHTML=['descriptive','diagnostic','predictive','prescriptive'].map(type=>`<article class="analytics-block ${type}"><h3>${type[0].toUpperCase()+type.slice(1)} Analytics</h3><p class="analytics-question">${questions[type]}</p>${values[type].map(item=>`<div class="analysis-entry"><h4>${esc(item.title)}</h4><p>${esc(item.text)}</p>${item.basis?`<small>Basis: ${esc(item.basis)}</small>`:''}</div>`).join('')}</article>`).join('');
}
function renderComparison(){
  $('comparisonCards').innerHTML=state.data.analytics.comparisons.map(item=>`<div class="compare-card"><div><h4>${esc(item.label)}</h4><p>${esc(item.basis)}</p></div><strong>${item.delta>0?'+':''}${fmt(item.delta,Math.abs(item.delta)%1?2:0)}${item.suffix==='pp'?' pp':item.suffix}</strong></div>`).join('');
}
function renderForecast(){
  if(!state.data)return; const a=state.data.analytics, actual=a.summary, ctx=$('forecastChart')?.getContext('2d');
  if(ctx){ makeChart('forecastChart','line',enrollmentTrendData(ctx, actual, a.forecast),chartOptions({forecastLegend:true})); }
  $('forecastValues').innerHTML=a.forecast.map(value=>`<div class="forecast-value"><small>${esc(value.school_year)}</small><strong>${fmt(value.enrollment)}</strong><span>projected students</span></div>`).join('')||'<p>Add more than one recorded year to project enrollment.</p>';
  const predictive=a.bi_tabs.enrollment.predictive;
  $('forecastAnalytics').innerHTML=`<h3>Forecast Interpretation</h3>${predictive.map(i=>`<div class="analysis-entry"><h4>${esc(i.title)}</h4><p>${esc(i.text)}</p><small>${esc(i.basis)}</small></div>`).join('')}`;
}

function renderActivities(){
  const list=state.data.activity || [];
  const filtered=state.activityType==='All'?list:list.filter(item=>item.section===state.activityType);
  const html=filtered.map(item=>`<div class="timeline-item"><span class="dot">${initials(item.display_name)}</span><div><p><strong>${esc(item.display_name)}</strong> ${esc(item.action.toLowerCase())}${item.affected_record?` · ${esc(item.affected_record)}`:''}</p><small>${new Date(item.occurred_at).toLocaleString()}</small></div></div>`).join('');
  $('recentActivity').innerHTML=(list.slice(0,5).map(item=>`<div class="timeline-item"><span class="dot">${initials(item.display_name)}</span><div><p><strong>${esc(item.display_name)}</strong> ${esc(item.action.toLowerCase())}</p><small>${new Date(item.occurred_at).toLocaleString()}</small></div></div>`).join('')||'<p>No recent activity yet.</p>');
  $('activityFull').innerHTML=html||'<p>No activity items match this filter.</p>';
}
function renderActions(){
  $('actionPlans').innerHTML=state.data.actions.map(item=>`<article class="action-card"><span class="action-status">${esc(item.status||'Suggested')} · ${esc(item.analysis_type||'Prescriptive')}</span><h3>${esc(item.focus_area)}</h3><p><strong>Observed Pattern:</strong> ${esc(item.observed_pattern)}</p><p class="data-basis"><strong>Data Basis:</strong> ${esc(item.data_basis||'Based on saved records.')}</p><p><strong>Suggested Action:</strong> ${esc(item.suggested_action)}</p><dl><div><dt>Target Indicator</dt><dd>${esc(item.target_indicator||'—')}</dd></div><div><dt>Monitoring Period</dt><dd>${esc(item.monitoring_period||'—')}</dd></div><div><dt>Baseline</dt><dd>${esc(item.baseline_value||'—')}</dd></div><div><dt>Target</dt><dd>${esc(item.target_value||'—')}</dd></div></dl><p class="monitor"><strong>Current Result:</strong> ${esc(item.current_result||'For monitoring')}<br><strong>Progress Notes:</strong> ${esc(item.progress_notes||'No progress update yet.')}</p><div class="action-buttons"><button class="edit-action" data-id="${item.id}">Edit Action Plan</button><button class="delete-action" data-id="${item.id}">Delete</button></div></article>`).join('');
  $$('.edit-action').forEach(button=>button.onclick=()=>openAction(Number(button.dataset.id)));
  $$('.delete-action').forEach(button=>button.onclick=async()=>{
    const id=Number(button.dataset.id);
    if(!confirm('Delete this action plan? This affects the dashboard and the next updated Excel export. You may use Undo Last Data Change immediately afterwards.')) return;
    try{await api(`/api/actions/${id}`,{method:'DELETE'});toast('Action plan deleted. Use Undo Last Data Change in School Records if needed.');await refreshData();}catch(err){toast(err.message,true);}
  });
}
function renderRecords(){
  const q=($('recordSearch')?.value||'').toLowerCase(); const selected=$('recordYear')?.value||'All Years';
  $('recordYear').innerHTML=`<option>All Years</option>${state.years.map(y=>`<option ${selected===y?'selected':''}>${y}</option>`).join('')}`;
  $('deleteYearBtn').disabled=selected==='All Years';
  const rows=state.data.records.filter(r=>(selected==='All Years'||r.school_year===selected) && (!q||Object.values(r).join(' ').toLowerCase().includes(q))).sort((a,b)=>b.school_year.localeCompare(a.school_year)||gradeLabels.indexOf(a.grade_level)-gradeLabels.indexOf(b.grade_level));
  const filteredResources=state.data.resources.filter(r=>selected==='All Years'||r.school_year===selected).sort((a,b)=>b.school_year.localeCompare(a.school_year));
  const filteredCohort=state.data.cohort.filter(r=>selected==='All Years'||r.school_year===selected).sort((a,b)=>b.school_year.localeCompare(a.school_year));
  const table=(id,field,label)=>{ $(id).innerHTML=`<thead><tr><th>School Year</th><th>Level</th><th>Grade Level</th><th>${label}</th><th>Action</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.school_year}</td><td>${r.level}</td><td>${r.grade_level}</td><td>${fmt(r[field])}</td><td><button class="edit-row" data-record="${r.id}">Edit</button></td></tr>`).join('')}</tbody>`; };
  table('enrollmentTable','enrollment','Enrollment'); table('dropoutTable','dropouts','Dropouts'); table('repeaterTable','repeaters','Repeaters'); table('teacherTable','teachers','Teachers');
  $('resourceTable').innerHTML=`<thead><tr><th>School Year</th><th>JHS Rooms</th><th>SHS Rooms</th><th>Total Rooms</th><th>Action</th></tr></thead><tbody>${filteredResources.map(r=>`<tr><td>${r.school_year}</td><td>${r.jhs_classrooms}</td><td>${r.shs_classrooms}</td><td>${Number(r.jhs_classrooms)+Number(r.shs_classrooms)}</td><td><button class="edit-resource" data-year="${r.school_year}">Edit</button></td></tr>`).join('')}</tbody>`;
  $('cohortTable').innerHTML=`<thead><tr><th>School Year</th><th>Baseline Year</th><th>Grade 7 Baseline</th><th>Grade 12</th><th>Action</th></tr></thead><tbody>${filteredCohort.map(r=>`<tr><td>${r.school_year}</td><td>${r.baseline_year}</td><td>${r.grade7_baseline}</td><td>${r.grade12_current}</td><td><button class="edit-cohort" data-year="${r.school_year}">Edit</button></td></tr>`).join('')}</tbody>`;
  $$('.edit-row').forEach(btn=>btn.onclick=()=>openRecord(Number(btn.dataset.record)));
  $$('.edit-resource').forEach(btn=>btn.onclick=()=>openResource(btn.dataset.year));
  $$('.edit-cohort').forEach(btn=>btn.onclick=()=>openCohort(btn.dataset.year));
}
function cohortBaselineYearFor(schoolYear){
  const match=String(schoolYear||'').trim().match(/^(\d{4})-(\d{4})$/);
  if(!match) return null;
  const start=Number(match[1])-5;
  return `${start}-${start+1}`;
}
function automaticBaselineForYear(schoolYear){
  const baselineYear=cohortBaselineYearFor(schoolYear);
  if(!baselineYear || !state.data) return {baselineYear, enrollment:null};
  const record=state.data.records.find(row=>row.school_year===baselineYear && row.grade_level==='Grade 7');
  return {baselineYear, enrollment:record ? Number(record.enrollment||0) : null};
}
function updateAutoBaseline(vals){
  const schoolYear=$('newYearName')?.value.trim() || '';
  const automatic=automaticBaselineForYear(schoolYear);
  const grade12=vals && vals.length >= 6 ? vals[5].e : 0;
  if(!schoolYear || !automatic.baselineYear){
    $('autoBaselineTitle').textContent='Enter a school year to locate the matching Grade 7 baseline.';
    $('autoBaselineNote').textContent='Grade 12 current enrollment will come automatically from the Grade 12 enrollment entered above.';
    $('autoBaselineValues').innerHTML='';
    $('manualBaselinePanel').classList.add('hidden');
    return automatic;
  }
  if(automatic.enrollment !== null){
    $('autoBaselineTitle').textContent=`Baseline found automatically from SY ${automatic.baselineYear}.`;
    $('autoBaselineNote').textContent='No manual baseline entry is needed. Grade 12 is read from the current new-year input above.';
    $('autoBaselineValues').innerHTML=`<div><small>Grade 7 Baseline</small><strong>${fmt(automatic.enrollment)}</strong></div><div><small>Current Grade 12</small><strong>${fmt(grade12)}</strong></div>`;
    $('manualBaselinePanel').classList.add('hidden');
  }else{
    $('autoBaselineTitle').textContent=`No Grade 7 record found for SY ${automatic.baselineYear}.`;
    $('autoBaselineNote').textContent='Enter a baseline below only when an official historical figure is available.';
    $('autoBaselineValues').innerHTML=`<div><small>Expected Baseline Year</small><strong>${esc(automatic.baselineYear)}</strong></div><div><small>Current Grade 12</small><strong>${fmt(grade12)}</strong></div>`;
    $('manualBaselinePanel').classList.remove('hidden');
    $('newCohortYear').value=automatic.baselineYear;
  }
  return automatic;
}
function renderNewYearInputs(){
  $('newYearInputs').innerHTML=gradeLabels.map(grade=>`<article class="grade-entry-card"><h4>${grade}</h4><label>Enrollment<input class="ny-enrollment" type="number" min="0" value="0"></label><label>Dropouts<input class="ny-dropouts" type="number" min="0" value="0"></label><label>Repeaters<input class="ny-repeaters" type="number" min="0" value="0"></label><label>Teachers<input class="ny-teachers" type="number" min="0" value="0"></label></article>`).join('');
  $$('#newYearInputs input').forEach(input=>input.addEventListener('input',updateNewYearPreview));
  $('newYearName')?.addEventListener('input',updateNewYearPreview);
  updateNewYearPreview();
}
function updateNewYearPreview(){
  const cards=$$('#newYearInputs .grade-entry-card');
  const vals=cards.map(c=>({e:Number(c.querySelector('.ny-enrollment').value||0),d:Number(c.querySelector('.ny-dropouts').value||0),r:Number(c.querySelector('.ny-repeaters').value||0),t:Number(c.querySelector('.ny-teachers').value||0)}));
  const total=vals.reduce((s,v)=>s+v.e,0), drop=vals.reduce((s,v)=>s+v.d,0), rep=vals.reduce((s,v)=>s+v.r,0), teacher=vals.reduce((s,v)=>s+v.t,0);
  const jhs=vals.slice(0,4).reduce((s,v)=>s+v.e,0), shs=vals.slice(4).reduce((s,v)=>s+v.e,0);
  updateAutoBaseline(vals);
  $('newYearPreview').innerHTML=[['JHS',jhs],['SHS',shs],['Total Enrollment',total],['Dropout Rate',total?`${(drop/total*100).toFixed(2)}%`:'—'],['Repeater Rate',total?`${(rep/total*100).toFixed(2)}%`:'—'],['Students / Teacher',teacher?`${(total/teacher).toFixed(1)}:1`:'—']].map(x=>`<div class="preview-chip">${x[0]} <strong>${x[1]}</strong></div>`).join('');
}
function renderAccounts(){
  const q=($('accountSearch').value||'').toLowerCase(); const accounts=state.data.accounts.filter(a=>!q||`${a.full_name} ${a.username}`.toLowerCase().includes(q));
  $('accountList').innerHTML=accounts.map(a=>`<article class="account-card">${avatarMarkup(a)}<div><h3>${esc(a.full_name)}</h3><p>@${esc(a.username)}</p><div class="masked">••••••••</div></div><div class="account-meta"><small>Last active: ${a.last_active?new Date(a.last_active).toLocaleString():'No login recorded'}</small><button class="edit-account" data-id="${a.id}">Edit</button></div></article>`).join('');
  $$('.edit-account').forEach(btn=>btn.onclick=()=>openAccount(Number(btn.dataset.id)));
  const self=state.data.accounts.find(a=>Number(a.id)===Number(window.SRNHS.account.id)); if(self && self.avatar_url){ $('topAvatar').innerHTML=`<img src="${esc(self.avatar_url)}" alt="Profile">`; }
}
function selectedQuery(){ const a=state.data.analytics; const years=a.selected_years.join(','); return `?years=${encodeURIComponent(years)}&level=${encodeURIComponent(a.level)}`; }
function renderReports(){
  const reports=[
    ['▣','Dashboard Summary Paper','Presentation-ready PDF with KPI summary, trend charts, analytical highlights, concerns, and suggested actions.',`/api/export/pdf/dashboard${selectedQuery()}`,'Download PDF'],
    ['◈','School Progress & Action Report','Usable PDF for annual review with current indicators, business-intelligence findings, and long-term action tracking.',`/api/export/pdf/progress${selectedQuery()}`,'Download PDF'],
    ['▤','Full Updated Excel Workbook','Formula-driven Excel workbook generated from all current saved dashboard records.',`/api/export/excel`,'Download Excel'],
    ['◫','School Records Workbook','Excel table export of current school records for additional review.',`/api/export/xlsx/records`,'Download Excel'],
    ['✦','Action Plans Workbook','Excel export of ongoing long-term action monitoring details.',`/api/export/xlsx/actions`,'Download Excel'],
    ['◷','Recent Activity Workbook','Excel export of recent dashboard activities.',`/api/export/xlsx/activity`,'Download Excel'],
    ['＋','New School Year Upload Template','Blank Excel format for encoding and uploading one additional school year.',`/api/export/template/new-year`,'Download Template'],
  ];
  $('reportGrid').innerHTML=reports.map(r=>`<article class="report-card"><span class="report-icon">${r[0]}</span><h3>${r[1]}</h3><p>${r[2]}</p><a href="${r[3]}">${r[4]}</a></article>`).join('');
}
function openRecord(id){ const row=state.data.records.find(r=>Number(r.id)===id); if(!row)return; $('editRecordId').value=id; $('editRecordYear').value=row.school_year; $('editRecordGrade').value=row.grade_level; $('editRecordLevel').value=row.level; $('editEnrollment').value=row.enrollment; $('editDropouts').value=row.dropouts; $('editRepeaters').value=row.repeaters; $('editTeachers').value=row.teachers; modal('recordModal'); }
function openResource(year){ const r=state.data.resources.find(x=>x.school_year===year); if(!r)return; $('editResourceYear').value=year; $('editJhsRooms').value=r.jhs_classrooms; $('editShsRooms').value=r.shs_classrooms; modal('resourceModal'); }
function openCohort(year){ const r=state.data.cohort.find(x=>x.school_year===year); if(!r)return; $('editCohortYear').value=year; $('editBaselineYear').value=r.baseline_year; $('editBaselineCount').value=r.grade7_baseline; $('editCurrentG12').value=r.grade12_current; modal('cohortModal'); }
function openAccount(id=null){
  const item=id?state.data.accounts.find(a=>Number(a.id)===id):null; $('accountModalTitle').textContent=item?'Edit Account Holder':'Add Account Holder'; $('editAccountId').value=item?.id||''; $('newAccountName').value=item?.full_name||''; $('newAccountUsername').value=item?.username||''; $('newAccountPassword').value=''; $('newAccountConfirm').value=''; $('newAccountAvatarData').value=item?.avatar_url||''; $('accountAvatarPreview').innerHTML=item?.avatar_url?`<img src="${esc(item.avatar_url)}" alt="Photo">`:(item?initials(item.full_name):'+'); $('deleteAccountBtn').classList.toggle('hidden',!item); modal('accountModal');
}
function openAction(id=null){
  const item=id?state.data.actions.find(a=>Number(a.id)===id):{}; $('actionModalTitle').textContent=id?'Edit Action Plan':'Add Action Plan'; $('editActionId').value=item.id||''; $('actionYear').value=item.school_year||state.data.analytics.latest.school_year; $('actionType').value=item.analysis_type||'Prescriptive'; $('actionArea').value=item.focus_area||''; $('actionPattern').value=item.observed_pattern||''; $('actionBasis').value=item.data_basis||''; $('actionText').value=item.suggested_action||''; $('actionGroup').value=item.responsible_group||''; $('actionIndicator').value=item.target_indicator||''; $('actionBaseline').value=item.baseline_value||''; $('actionTarget').value=item.target_value||''; $('actionPeriod').value=item.monitoring_period||''; $('actionResult').value=item.current_result||''; $('actionStatus').value=item.status||'Suggested'; $('actionProgress').value=item.progress_notes||''; $('actionNotes').value=item.notes||''; modal('actionModal');
}
async function resizeImage(input, hiddenId, previewId){ const file=input.files[0]; if(!file)return; if(file.size>4*1024*1024){toast('Photo must be smaller than 4 MB.',true);return;} const url=URL.createObjectURL(file); const image=new Image(); image.onload=()=>{ const canvas=document.createElement('canvas'), size=180; canvas.width=size;canvas.height=size; const ctx=canvas.getContext('2d'); const min=Math.min(image.width,image.height), sx=(image.width-min)/2, sy=(image.height-min)/2; ctx.drawImage(image,sx,sy,min,min,0,0,size,size); const value=canvas.toDataURL('image/jpeg',.82); $(hiddenId).value=value; $(previewId).innerHTML=`<img src="${value}" alt="Photo preview">`; URL.revokeObjectURL(url); }; image.src=url; }
function bindForms(){
  $$('[data-modal]').forEach(btn=>btn.addEventListener('click',()=>modal(btn.dataset.modal)));
  $$('[data-close]').forEach(btn=>btn.addEventListener('click',()=>modal(btn.dataset.close,false)));
  $('profileToggle').onclick=()=>$('profileMenu').classList.toggle('open'); $('addAccountBtn').onclick=()=>openAccount(); $('addActionBtn').onclick=()=>openAction(); $('addYearBtn').onclick=()=>{showPage('records');activateTab('records','addyear');};
  $('recordSearch').addEventListener('input',renderRecords); $('recordYear').addEventListener('change',renderRecords); $('accountSearch').addEventListener('input',renderAccounts);
  $('deleteYearBtn').onclick=async()=>{const year=$('recordYear').value;if(!year||year==='All Years')return; if(!confirm(`Delete all saved records for SY ${year}? This will be removed from dashboard views and future Excel downloads. You can restore the latest deletion using Undo Last Data Change.`)) return; try{await api(`/api/years/${encodeURIComponent(year)}`,{method:'DELETE'});toast(`SY ${year} deleted. You may use Undo Last Data Change to restore it.`); state.allYears=true; await refreshData();}catch(err){toast(err.message,true);}};
  $('undoDataBtn').onclick=async()=>{if(!confirm('Restore the dashboard data to the state before the most recent saved change?')) return; try{const result=await api('/api/undo',{method:'POST'});toast(result.message);state.allYears=true;await refreshData();}catch(err){toast(err.message,true);}};
  $$('.activity-filters button').forEach(btn=>btn.onclick=()=>{state.activityType=btn.dataset.activity;$$('.activity-filters button').forEach(b=>b.classList.toggle('selected',b===btn));renderActivities();});
  $('newAccountAvatar').onchange=e=>resizeImage(e.target,'newAccountAvatarData','accountAvatarPreview'); $('profileAvatar').onchange=e=>resizeImage(e.target,'profileAvatarData','topAvatar');
  $('recordForm').onsubmit=async e=>{e.preventDefault(); if(!confirm('Save these school-record changes? Updated figures will be used in charts, analytics, reports and the next Excel download.')) return; try{await api('/api/records',{method:'POST',body:JSON.stringify({school_year:$('editRecordYear').value,grade_level:$('editRecordGrade').value,level:$('editRecordLevel').value,enrollment:$('editEnrollment').value,dropouts:$('editDropouts').value,repeaters:$('editRepeaters').value,teachers:$('editTeachers').value})});modal('recordModal',false);toast('School record saved. Analytics and Excel export will reflect the change.');await refreshData();}catch(err){toast(err.message,true);}};
  $('resourceForm').onsubmit=async e=>{e.preventDefault();if(!confirm('Save these classroom changes? This will update resource analytics and the next Excel download.')) return;try{await api('/api/resources',{method:'POST',body:JSON.stringify({school_year:$('editResourceYear').value,jhs_classrooms:$('editJhsRooms').value,shs_classrooms:$('editShsRooms').value})});modal('resourceModal',false);toast('Classroom record saved.');await refreshData();}catch(err){toast(err.message,true);}};
  $('cohortForm').onsubmit=async e=>{e.preventDefault();if(!confirm('Save these cohort changes? This will update continuity analytics and the next Excel download.')) return;try{await api('/api/cohort',{method:'POST',body:JSON.stringify({school_year:$('editCohortYear').value,baseline_year:$('editBaselineYear').value,grade7_baseline:$('editBaselineCount').value,grade12_current:$('editCurrentG12').value})});modal('cohortModal',false);toast('Cohort record saved.');await refreshData();}catch(err){toast(err.message,true);}};
  $('saveYearBtn').onclick=async()=>{ if(!confirm('Save this new school year? It will appear in all dashboard analytics and in the next updated Excel download.')) return; const grades=$$('#newYearInputs .grade-entry-card').map((card,index)=>({grade_level:gradeLabels[index],enrollment:card.querySelector('.ny-enrollment').value,dropouts:card.querySelector('.ny-dropouts').value,repeaters:card.querySelector('.ny-repeaters').value,teachers:card.querySelector('.ny-teachers').value})); const automatic=automaticBaselineForYear($('newYearName').value); const fallback=automatic.enrollment===null ? {baseline_year:$('newCohortYear')?.value||'',grade7_baseline:$('newCohortBase')?.value||'',grade12_current:grades[5].enrollment} : {}; try{const out=await api('/api/years',{method:'POST',body:JSON.stringify({school_year:$('newYearName').value,grades,resources:{jhs_classrooms:$('newJhsRooms').value,shs_classrooms:$('newShsRooms').value},cohort:fallback})});toast(out.message + (out.cohort_message ? ` ${out.cohort_message}` : ''));state.allYears=true;await refreshData();}catch(err){toast(err.message,true);}};
  $('excelUploadForm').onsubmit=async e=>{e.preventDefault();const file=$('excelFile').files[0];if(!file)return;const mode=$('excelSyncMode').value;const warning=mode==='replace'?'Full Sync will make dashboard records match this workbook, including removed school years or rows. Continue? You may immediately use Undo Last Data Change.':'Add or update values from this workbook? Existing records not included in the upload will remain saved.';if(!confirm(warning)) return;const body=new FormData();body.append('file',file);body.append('sync_mode',mode);try{const out=await api('/api/upload-excel',{method:'POST',body});const baselineNote=out.auto_baselines && out.auto_baselines.length ? ` Automatic cohort baseline generated for: ${out.auto_baselines.join(', ')}.` : '';toast(`${out.message} ${out.record_count} records processed; years: ${out.years.join(', ')}.${baselineNote}`);state.allYears=true;await refreshData();}catch(err){toast(err.message,true);}};
  $('accountForm').onsubmit=async e=>{e.preventDefault();const id=$('editAccountId').value,password=$('newAccountPassword').value,confirm=$('newAccountConfirm').value;if(password!==confirm){toast('Passwords do not match.',true);return;}const body={full_name:$('newAccountName').value,username:$('newAccountUsername').value,password,avatar_url:$('newAccountAvatarData').value};try{await api(id?`/api/accounts/${id}`:'/api/accounts',{method:id?'PATCH':'POST',body:JSON.stringify(body)});modal('accountModal',false);toast(id?'Account holder updated.':'Account holder added.');await refreshData();}catch(err){toast(err.message,true);}};
  $('deleteAccountBtn').onclick=async()=>{const id=$('editAccountId').value;if(!id||!confirm('Delete this account holder?'))return;try{await api(`/api/accounts/${id}`,{method:'DELETE'});modal('accountModal',false);toast('Account holder deleted.');await refreshData();}catch(err){toast(err.message,true);}};
  $('actionForm').onsubmit=async e=>{e.preventDefault();if(!confirm('Save this action plan? It will be included in long-term monitoring and report exports.')) return;const id=$('editActionId').value;const body={school_year:$('actionYear').value,analysis_type:$('actionType').value,focus_area:$('actionArea').value,observed_pattern:$('actionPattern').value,data_basis:$('actionBasis').value,suggested_action:$('actionText').value,responsible_group:$('actionGroup').value,target_indicator:$('actionIndicator').value,baseline_value:$('actionBaseline').value,target_value:$('actionTarget').value,monitoring_period:$('actionPeriod').value,current_result:$('actionResult').value,status:$('actionStatus').value,progress_notes:$('actionProgress').value,notes:$('actionNotes').value};try{await api(id?`/api/actions/${id}`:'/api/actions',{method:id?'PATCH':'POST',body:JSON.stringify(body)});modal('actionModal',false);toast(id?'Action plan updated.':'Action plan added.');await refreshData();}catch(err){toast(err.message,true);}};
  $('profileForm').onsubmit=async e=>{e.preventDefault();const password=$('profilePassword').value,confirm=$('profileConfirm').value;if(password!==confirm){toast('Passwords do not match.',true);return;}try{const result=await api(`/api/accounts/${window.SRNHS.account.id}`,{method:'PATCH',body:JSON.stringify({full_name:$('profileName').value,username:$('profileUsername').value,password,avatar_url:$('profileAvatarData').value||undefined})});$('displayName').textContent=result.account.full_name;$('displayUsername').textContent='@'+result.account.username;window.SRNHS.account=result.account;modal('profileModal',false);toast('Your account details were updated.');await refreshData();}catch(err){toast(err.message,true);}};
  $('displayForm').onsubmit=async e=>{e.preventDefault();const body={dashboard_title:$('settingTitle').value,school_name:$('settingSchool').value,location:$('settingLocation').value,subtitle:$('settingSubtitle').value,main_green:$('settingGreen').value,sidebar_color:$('settingSidebar').value};try{await api('/api/settings',{method:'PATCH',body:JSON.stringify(body)});modal('displayModal',false);toast('Dashboard display settings updated. Refreshing...');setTimeout(()=>location.reload(),900);}catch(err){toast(err.message,true);}};
}
function scenarioBind(){ const update=()=>{if(!state.data)return;const a=state.data.analytics,year=$('scenarioYear').value||a.years.slice(-1)[0],summary=a.all_summary.find(r=>r.school_year===year)||a.latest,change=Number($('enrollmentChange').value),scenario=Math.round(summary.enrollment*(1+change/100));$('changeValue').textContent=`${change}%`;$('scenarioEnrollment').textContent=fmt(scenario);$('scenarioDifference').textContent=`${scenario-summary.enrollment>=0?'+':''}${fmt(scenario-summary.enrollment)} compared with base year`;const target=Number($('transitionTarget').value);$('transitionTargetValue').textContent=`${target}%`;const prevG10=a.latest.previous_grade10||0,currentG11=a.latest.current_grade11||0,estimate=Math.round(prevG10*target/100);$('scenarioG11').textContent=fmt(estimate);$('scenarioG11Difference').textContent=`${estimate-currentG11>=0?'+':''}${estimate-currentG11} compared with current Grade 11`;const repRate=Number($('repeatTarget').value);$('repeatTargetValue').textContent=`${repRate.toFixed(2)}%`;const rep=Math.round(scenario*repRate/100);$('scenarioRepeaters').textContent=fmt(rep);$('repeaterDifference').textContent=`${Math.max(summary.repeaters-rep,0)} fewer than base-year repeaters`;const teachers=Number($('scenarioTeachers').value||1);$('scenarioSTRatio').textContent=`${(scenario/teachers).toFixed(1)}:1`;}; ['enrollmentChange','transitionTarget','repeatTarget','scenarioTeachers','scenarioYear'].forEach(id=>$(id).addEventListener('input',update)); return update; }
let updateScenario;
function renderScenario(){const a=state.data.analytics;$('scenarioYear').innerHTML=a.years.map(y=>`<option value="${y}" ${y===a.years.slice(-1)[0]?'selected':''}>${y}</option>`).join(''); updateScenario();}
function bindSearch(){ $('globalSearch').addEventListener('keydown',event=>{if(event.key!=='Enter')return;const term=event.target.value.trim().toLowerCase();if(!term)return;if(term.includes('account')||term.includes('activity')){showPage('accounts');activateTab('accounts',term.includes('activity')?'activity':'holders');}else if(term.includes('report')||term.includes('download')||term.includes('pdf'))showPage('reports');else if(term.includes('action')||term.includes('insight')||term.includes('forecast')||term.includes('concern'))showPage('insights');else if(term.includes('record')||term.includes('upload')||term.includes('add year'))showPage('records');else showPage('analytics');}); }
function renderEverything(){renderYearPills();renderKpis();renderCharts();renderComparison();renderIntelligence();renderActivities();renderActions();renderRecords();updateNewYearPreview();renderAccounts();renderReports();renderScenario();}
document.addEventListener('DOMContentLoaded',async()=>{bindNavigation();bindFilters();bindForms();bindSearch();renderNewYearInputs();updateScenario=scenarioBind();await refreshData(true);});
