
<template>
  <section class="grid">
    <div v-if="task && !canReviewResult" class="panel panel--hero detail-hero">
      <div class="detail-hero__main">
        <div class="detail-hero__eyebrow">
          <div class="task-kind-badges detail-type-badges">
            <span class="task-kind-badge" :class="taskTypeClass(task.task_type)">
              {{ task.task_type }}
            </span>
            <span v-if="showScannerEngine" class="task-kind-badge task-kind-badge--engine">
              {{ scannerEngineLabel }}
            </span>
          </div>
          <span class="detail-hero__badge">{{ detailHeroBadge }}</span>
          <span class="muted">任务 #{{ displayTaskNo }}</span>
        </div>
        <div class="detail-hero__title-row">
          <h2>{{ detailHeadline }}</h2>
          <span class="detail-hero__status">{{ statusTone.label }}</span>
        </div>
        <p class="detail-hero__lead">{{ detailSubline }}</p>
        <div class="detail-next-step">
          <span class="detail-next-step__label">推荐先做</span>
          <strong>{{ primaryAction.title }}</strong>
          <p>{{ primaryAction.detail }}</p>
        </div>
        <div class="report-pill-row detail-hero__pills">
          <span class="report-pill">当前状态：{{ task.status }}</span>
          <span class="report-pill">扫描目标：{{ currentTargetLabel }}</span>
          <span class="report-pill">创建时间：{{ formatDateTime(task.created_at) }}</span>
          <span class="report-pill">总耗时：{{ formatDuration(task.duration_ms) }}</span>
        </div>
        <div class="detail-hero__meta">
          <span v-for="item in detailHeroHighlights" :key="item">{{ item }}</span>
        </div>
        <div class="muted" v-if="autoRefreshHint">{{ autoRefreshHint }}</div>
        <div class="error" v-if="errorMessage">{{ errorMessage }}</div>
        <div class="success" v-if="actionMessage">{{ actionMessage }}</div>
      </div>

      <div class="detail-hero__aside">
        <div class="detail-status-card" :class="statusTone.className">
          <span class="risk-emblem__label">执行状态</span>
          <strong>{{ statusTone.label }}</strong>
          <p>{{ statusTone.description }}</p>
        </div>

        <div class="detail-hero__actions">
          <button
            v-for="action in detailActions"
            :key="action.key"
            class="button detail-action-button"
            :class="{ secondary: !action.primary }"
            type="button"
            @click="action.handler"
          >
            {{ action.label }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="isDastReport && task && result" class="grid">
      <ReportHero
        anchor-id="detail-report"
        kicker="DAST Security Report"
        title="动态安全扫描报告"
        :badge="reportHeroBadge"
        :sharp-summary="dastSharpConclusion"
        :pills="dastHeroPills"
        :meta-items="dastHeroMeta"
        :risk-tone="riskTone"
        :actions="detailActions"
        :show-return-link="showAdminReturn"
        variant="serious"
        @back="goBackToList"
      />

      <ActionBanner
        v-if="highRiskCount > 0"
        :title="`${highRiskCount} 个高/严重风险漏洞需在 24h 内处置`"
        :message="dastTopRiskTypeHint"
        cta-label="查看漏洞 →"
        @cta="scrollToIssues"
      />

      <SeverityTileGrid :distribution="result.severity_distribution || {}" />

      <div class="grid two report-two-col">
        <div class="panel report-panel">
          <div class="report-section-head"><div><h3>风险等级分布</h3><div class="muted">展示本次扫描中不同严重度问题的占比结构。</div></div></div>
          <div class="severity-chart-card" v-if="severityChart.length">
            <SeverityDonutChart
              :data="severityChart"
              :total="result.issue_count ?? 0"
              center-label="总漏洞数"
            />
            <div class="severity-legend">
              <div v-for="item in severityChart" :key="`legend-${item.label}`" class="severity-legend__item">
                <span class="severity-legend__dot" :class="severityToneClass(item.label)"></span>
                <span>{{ severityLabel(item.label) }}</span>
                <strong>{{ item.count }}</strong>
              </div>
            </div>
          </div>
          <div class="muted" v-else>本次扫描未形成可展示的风险等级分布。</div>
        </div>

        <div class="panel report-panel">
          <div class="report-section-head"><div><h3>漏洞类型分布</h3><div class="muted">展示本次结果中最主要的漏洞类别及其频次。</div></div></div>
          <div v-if="typeChart.length" class="chart-list chart-list--compact">
            <div v-for="item in typeChart" :key="`type-${item.label}`" class="chart-row">
              <div class="chart-row__meta"><span>{{ dastCategoryLabel(item.label) }}</span><strong>{{ item.count }}</strong></div>
              <div class="chart-bar"><div class="chart-bar__fill chart-bar__fill--neutral" :style="{ width: `${item.percent}%` }"></div></div>
            </div>
          </div>
          <div class="muted" v-else>本次扫描未形成明显的漏洞类型分布。</div>
        </div>
      </div>

      <div class="panel report-panel" v-if="owaspChart.length">
        <div class="report-section-head"><div><h3>OWASP Top 10 分类映射</h3><div class="muted">将本次漏洞发现映射到 OWASP Top 10 标准分类，评估目标系统在各安全维度的暴露形状。</div></div></div>
        <OwaspRadarChart :data="owaspChart" />
      </div>

      <div id="detail-issues" class="panel report-panel">
        <div class="report-section-head">
          <div><h3>漏洞清单</h3><div class="muted">支持按严重度、类别和路径筛选；点击行查看证据与 AI 解读。</div></div>
        </div>
        <IssueTable
          :issues="issues"
          :columns="dastIssueColumns"
          :filter="dastIssueFilter"
          @row-click="openIssueDrawer"
        />
      </div>

      <AdvicePanel :tabs="dastAdviceTabs" />

      <div class="panel report-panel">
        <div class="report-section-head"><div><h3>扫描元信息</h3><div class="muted">记录本次动态扫描的执行范围与基础上下文。</div></div></div>
        <div class="meta-grid">
          <div class="meta-item"><span class="muted">扫描目标</span><strong>{{ result.target_url || '-' }}</strong></div>
          <div class="meta-item"><span class="muted">扫描范围</span><strong>{{ result.scan_scope || '-' }}</strong></div>
          <div class="meta-item"><span class="muted">任务开始时间</span><strong>{{ task.started_at || '-' }}</strong></div>
          <div class="meta-item"><span class="muted">任务结束时间</span><strong>{{ task.finished_at || '-' }}</strong></div>
          <div class="meta-item"><span class="muted">附加发现</span><strong>{{ result.additional_count ?? 0 }}</strong></div>
          <div class="meta-item"><span class="muted">报告文件</span><strong>{{ task.report_path || '-' }}</strong></div>
        </div>
      </div>

      <details class="panel report-panel">
        <summary class="report-collapse-title">附录：任务元信息与原始数据</summary>
        <div class="grid two" style="margin-top: 16px;">
          <div class="panel"><h4>任务元信息</h4><p>任务名称：{{ task.task_name || '-' }}</p><p>任务状态：{{ task.status }}</p><p>任务创建时间：{{ task.created_at }}</p><p>错误信息：{{ task.error_message || '-' }}</p></div>
          <div class="panel"><h4>扫描摘要</h4><p>{{ result.summary || '-' }}</p></div>
        </div>
        <div class="panel" style="margin-top: 16px;"><h4>原始结果 JSON</h4><pre>{{ JSON.stringify(result, null, 2) }}</pre></div>
      </details>
    </div>

    <div v-else-if="isScaReport && task && result" class="grid">
      <ReportHero
        anchor-id="detail-report"
        kicker="SCA Dependency Audit Report"
        title="依赖组件安全报告"
        :badge="reportHeroBadge"
        :sharp-summary="scaSharpConclusion"
        :pills="scaHeroPills"
        :meta-items="scaHeroMeta"
        :risk-tone="riskTone"
        risk-label="依赖风险等级"
        :actions="detailActions"
        :show-return-link="showAdminReturn"
        @back="goBackToList"
      />

      <ActionBanner
        v-if="scaHighRiskCount > 0"
        :title="`${scaHighRiskCount} 个高/严重风险依赖漏洞需立即处置`"
        :message="scaTopRiskHint"
        cta-label="查看清单 →"
        @cta="scrollToIssues"
      />

      <SeverityTileGrid
        v-if="result.severity_distribution"
        :distribution="result.severity_distribution"
      />

      <div class="grid two report-two-col">
        <div class="panel report-panel">
          <div class="report-section-head"><div><h3>漏洞包分布</h3><div class="muted">展示依赖风险集中在哪些 Python 包上。</div></div></div>
          <div v-if="packageChart.length" class="chart-list chart-list--compact">
            <div v-for="item in packageChart" :key="`sca-package-${item.label}`" class="chart-row">
              <div class="chart-row__meta"><span>{{ item.label }}</span><strong>{{ item.count }}</strong></div>
              <div class="chart-bar"><div class="chart-bar__fill chart-bar__fill--neutral" :style="{ width: `${item.percent}%` }"></div></div>
            </div>
          </div>
          <div class="muted" v-else>本次扫描未形成漏洞包分布。</div>
        </div>

        <div class="panel report-panel">
          <div class="report-section-head"><div><h3>扫描概览</h3><div class="muted">本次依赖扫描的整体面板信息。</div></div></div>
          <div class="meta-grid">
            <div class="meta-item"><span class="muted">依赖总数</span><strong>{{ result.dependency_count ?? 0 }}</strong></div>
            <div class="meta-item"><span class="muted">漏洞总数</span><strong :class="{ 'text-danger': (result.vulnerability_count ?? 0) > 0 }">{{ result.vulnerability_count ?? 0 }}</strong></div>
            <div class="meta-item"><span class="muted">可修复项</span><strong>{{ result.fixable_count ?? 0 }}</strong></div>
            <div class="meta-item"><span class="muted">重点包</span><strong class="text-wrap">{{ topPackageLabel }}</strong></div>
          </div>
        </div>
      </div>

      <div id="detail-issues" class="panel report-panel">
        <div class="report-section-head">
          <div><h3>依赖漏洞清单</h3><div class="muted">支持按严重度、依赖包筛选和漏洞编号搜索；点击行查看说明与升级建议。</div></div>
        </div>
        <IssueTable
          :issues="issues"
          :columns="scaIssueColumns"
          :filter="scaIssueFilter"
          empty-message="当前没有可展示的依赖漏洞明细。"
          @row-click="openIssueDrawer"
        />
      </div>

      <AdvicePanel :tabs="scaAdviceTabs" />

      <details class="panel report-panel">
        <summary class="report-collapse-title">附录：任务元信息与原始数据</summary>
        <div class="grid two" style="margin-top: 16px;">
          <div class="panel"><h4>任务元信息</h4><p>任务名称：{{ task.task_name || '-' }}</p><p>任务状态：{{ task.status }}</p><p>任务创建时间：{{ task.created_at }}</p><p>目标路径：{{ displayTargetName }}</p></div>
          <div class="panel"><h4>扫描摘要</h4><p>{{ result.summary || task.result_summary || '-' }}</p></div>
        </div>
        <div class="panel" style="margin-top: 16px;"><h4>原始结果 JSON</h4><pre>{{ JSON.stringify(result, null, 2) }}</pre></div>
      </details>
    </div>

    <div v-else-if="isSastReport && task && result" class="grid">
      <ReportHero
        anchor-id="detail-report"
        kicker="SAST Security Report"
        title="静态代码审计报告"
        :badge="reportHeroBadge"
        :sharp-summary="sastSharpConclusion"
        :pills="sastHeroPills"
        :meta-items="sastHeroMeta"
        :risk-tone="riskTone"
        :actions="detailActions"
        :show-return-link="showAdminReturn"
        @back="goBackToList"
      >
        <template v-if="showScannerEngine" #badges>
          <div class="task-kind-badges detail-type-badges detail-type-badges--report">
            <span class="task-kind-badge task-kind-badge--sast">SAST</span>
            <span class="task-kind-badge task-kind-badge--engine">{{ scannerEngineLabel }}</span>
          </div>
        </template>
      </ReportHero>

      <ActionBanner
        v-if="sastHighRiskCount > 0"
        :title="`${sastHighRiskCount} 个高危代码问题需优先处理`"
        :message="sastTopRiskHint"
        cta-label="查看问题 →"
        @cta="scrollToIssues"
      />

      <SeverityTileGrid :distribution="result.severity_distribution || {}" />

      <div class="grid two report-two-col">
        <div class="panel report-panel">
          <div class="report-section-head"><div><h3>严重度分布</h3><div class="muted">展示本次代码审计中不同风险等级问题的占比结构。</div></div></div>
          <div class="severity-chart-card" v-if="severityChart.length">
            <SeverityDonutChart
              :data="severityChart"
              :total="result.issue_count ?? 0"
              center-label="总问题数"
            />
            <div class="severity-legend">
              <div v-for="item in severityChart" :key="`sast-legend-${item.label}`" class="severity-legend__item"><span class="severity-legend__dot" :class="severityToneClass(item.label)"></span><span>{{ severityLabel(item.label) }}</span><strong>{{ item.count }}</strong></div>
            </div>
          </div>
          <div class="muted" v-else>本次扫描未形成可展示的严重度分布。</div>
        </div>

        <div class="panel report-panel">
          <div class="report-section-head"><div><h3>规则类型分布</h3><div class="muted">展示本次结果中出现频次最高的规则类型。</div></div></div>
          <div v-if="typeChart.length" class="chart-list chart-list--compact">
            <div v-for="item in typeChart" :key="`sast-type-${item.label}`" class="chart-row">
              <div class="chart-row__meta"><span>{{ sastRuleLabel(item.label) }}</span><strong>{{ item.count }}</strong></div>
              <div class="chart-bar"><div class="chart-bar__fill chart-bar__fill--neutral" :style="{ width: `${item.percent}%` }"></div></div>
            </div>
          </div>
          <div class="muted" v-else>本次扫描未形成明显的规则分布。</div>
        </div>
      </div>

      <div class="panel report-panel" v-if="owaspChart.length">
        <div class="report-section-head"><div><h3>OWASP Top 10 分类映射</h3><div class="muted">将本次发现的问题映射到 OWASP Top 10 标准分类，便于对标行业标准评估代码安全状况。</div></div></div>
        <OwaspRadarChart :data="owaspChart" />
      </div>

      <div class="grid two report-two-col">
        <div class="panel report-panel">
          <div class="report-section-head"><div><h3>置信度分布</h3><div class="muted">反映工具对当前问题判断的可信程度。</div></div></div>
          <div v-if="confidenceChart.length" class="chart-list chart-list--compact">
            <div v-for="item in confidenceChart" :key="`conf-${item.label}`" class="chart-row"><div class="chart-row__meta"><span>{{ confidenceLabel(item.label) }}</span><strong>{{ item.count }}</strong></div><div class="chart-bar"><div class="chart-bar__fill" :class="severityToneClass(item.label)" :style="{ width: `${item.percent}%` }"></div></div></div>
          </div>
          <div class="muted" v-else>暂无置信度分布。</div>
        </div>
        <div class="panel report-panel">
          <div class="report-section-head"><div><h3>文件分布</h3><div class="muted">按方块面积展示问题集中的文件，hover 查看完整路径和数量。</div></div></div>
          <FileTreemapChart v-if="fileChart.length" :data="fileChart" />
          <div class="muted" v-else>暂无文件分布。</div>
        </div>
      </div>

      <div id="detail-issues" class="panel report-panel">
        <div class="report-section-head">
          <div><h3>问题清单</h3><div class="muted">支持按严重度、规则筛选和代码片段搜索；点击行查看证据与 AI 解读。</div></div>
        </div>
        <IssueTable
          :issues="issues"
          :columns="sastIssueColumns"
          :filter="sastIssueFilter"
          empty-message="当前没有可展示的代码问题明细。"
          @row-click="openIssueDrawer"
        />
      </div>

      <AdvicePanel :tabs="sastAdviceTabs" />

      <details class="panel report-panel">
        <summary class="report-collapse-title">附录：任务元信息与原始数据</summary>
        <div class="grid two" style="margin-top: 16px;">
          <div class="panel"><h4>任务元信息</h4><p>任务名称：{{ task.task_name || '-' }}</p><p>任务状态：{{ task.status }}</p><p>任务创建时间：{{ task.created_at }}</p><p>目标路径：{{ displayTargetName }}</p></div>
          <div class="panel"><h4>扫描摘要</h4><p>{{ result.summary || task.result_summary || '-' }}</p></div>
        </div>
        <div class="panel" style="margin-top: 16px;"><h4>原始结果 JSON</h4><pre>{{ JSON.stringify(result, null, 2) }}</pre></div>
      </details>
    </div>

    <div v-else class="panel detail-state-panel">
      <div v-if="task" class="empty-state">
        <h4>{{ statusTone.label }}</h4>
        <p>{{ detailSubline }}</p>
        <p class="muted" v-if="autoRefreshHint">{{ autoRefreshHint }}</p>
        <div class="form-actions">
          <button class="button secondary" @click="loadDetail">刷新状态</button>
          <button class="button" v-if="!canDownloadReport" @click="rerunCurrentTask">重新执行</button>
        </div>
      </div>
      <div class="muted" v-else-if="!errorMessage">正在加载任务详情...</div>
      <div class="error" v-if="errorMessage">{{ errorMessage }}</div>
    </div>

    <IssueDrawer
      :open="drawerOpen"
      :level="drawerLevel"
      :title="drawerTitle"
      :subtitle="drawerSubtitle"
      @close="closeIssueDrawer"
    >
      <template v-if="drawerIssue">
        <div v-if="isDastReport" class="report-issue-body report-issue-body--compact">
          <div class="report-issue-block report-issue-block--source">
            <span class="report-issue-block__label">原始扫描结果</span>
            <p>{{ getDastIssueSummary(drawerIssue) }}</p>
            <div class="issue-facts">
              <span class="issue-fact" :class="{ 'issue-fact--danger': ['HIGH','CRITICAL'].includes((drawerIssue.level || '').toUpperCase()) }">{{ severityLabel(drawerIssue.level) }}</span>
              <span class="issue-fact">{{ drawerIssue.method || '-' }}</span>
              <span class="issue-fact">{{ drawerIssue.parameter || '无参数' }}</span>
            </div>
          </div>
          <div class="report-issue-block report-issue-block--evidence">
            <span class="report-issue-block__label">证据线索</span>
            <p>{{ getDastIssueEvidence(drawerIssue) }}</p>
          </div>
          <div class="report-issue-block">
            <span class="report-issue-block__label">影响分析</span>
            <p>{{ getDastIssueImpact(drawerIssue) }}</p>
          </div>
          <div class="report-issue-block">
            <span class="report-issue-block__label">整改建议</span>
            <p>{{ getDastIssueRecommendation(drawerIssue) }}</p>
          </div>
        </div>
        <div v-else-if="isSastReport" class="report-issue-body report-issue-body--compact">
          <div class="report-issue-block report-issue-block--source">
            <span class="report-issue-block__label">原始扫描结果</span>
            <p>{{ getSastIssueSummary(drawerIssue) }}</p>
            <div class="issue-facts">
              <span class="issue-fact" :class="{ 'issue-fact--danger': (drawerIssue.issue_severity || '').toUpperCase() === 'HIGH' }">{{ severityLabel(drawerIssue.issue_severity) }}</span>
              <span class="issue-fact">置信度 {{ confidenceLabel(drawerIssue.issue_confidence) }}</span>
              <span class="issue-fact issue-fact--code">{{ drawerIssue.test_id || 'RULE' }}</span>
            </div>
          </div>
          <div class="report-issue-block report-issue-block--evidence">
            <span class="report-issue-block__label">证据线索</span>
            <p>{{ getSastIssueEvidence(drawerIssue) }}</p>
          </div>
          <div class="report-issue-block">
            <span class="report-issue-block__label">影响分析</span>
            <p>{{ getSastIssueImpact(drawerIssue) }}</p>
          </div>
          <div class="report-issue-block">
            <span class="report-issue-block__label">整改建议</span>
            <p>{{ getSastIssueRecommendation(drawerIssue) }}</p>
          </div>
        </div>
        <div v-else-if="isScaReport" class="report-issue-body report-issue-body--compact">
          <div class="report-issue-block report-issue-block--source">
            <span class="report-issue-block__label">漏洞说明</span>
            <p>{{ getScaIssueSummary(drawerIssue) }}</p>
            <div class="issue-facts">
              <span class="issue-fact" :class="{ 'issue-fact--danger': ['HIGH','CRITICAL'].includes((drawerIssue.severity || '').toUpperCase()) }">{{ severityLabel(drawerIssue.severity) }}</span>
              <span class="issue-fact">{{ drawerIssue.installed_version || '-' }}</span>
              <span class="issue-fact issue-fact--code">{{ drawerIssue.vulnerability_id || '-' }}</span>
            </div>
          </div>
          <div class="report-issue-block report-issue-block--evidence">
            <span class="report-issue-block__label">证据线索</span>
            <p>{{ getScaIssueEvidence(drawerIssue) }}</p>
          </div>
          <div class="report-issue-block">
            <span class="report-issue-block__label">影响分析</span>
            <p>{{ getScaIssueImpact(drawerIssue) }}</p>
          </div>
          <div class="report-issue-block">
            <span class="report-issue-block__label">整改建议</span>
            <p>{{ getScaIssueRecommendation(drawerIssue) }}</p>
          </div>
        </div>
        <details
          class="report-detail-box report-detail-box--action"
          v-if="drawerEvidenceText"
        >
          <summary class="report-detail-box__action">{{ drawerEvidenceLabel }}</summary>
          <pre class="issue-code">{{ drawerEvidenceText }}</pre>
          <p
            class="report-appendix-note"
            v-if="isSastReport && drawerIssue.more_info"
          >{{ drawerIssue.more_info }}</p>
        </details>
        <div class="ai-insight-box">
          <div class="ai-insight-box__head">
            <div>
              <div class="report-issue-block__label report-issue-block__label--ai">AI 解读增强</div>
              <p class="muted">聚焦问题含义、风险后果、修复动作与复测方式。</p>
            </div>
            <button
              class="button secondary"
              type="button"
              @click="loadIssueInsight(drawerIssue.id)"
              :disabled="isInsightLoading(drawerIssue.id)"
            >
              {{ isInsightLoading(drawerIssue.id) ? '生成中...' : (getIssueInsight(drawerIssue.id) ? '重新生成' : '生成解读') }}
            </button>
          </div>
          <div class="ai-insight-summary" v-if="getIssueInsight(drawerIssue.id)"><strong>AI 总结：</strong>{{ getInsightSummary(drawerIssue.id) }}</div>
          <div class="muted" v-if="isInsightLoading(drawerIssue.id)">AI 正在生成解读...</div>
          <div class="error" v-else-if="getInsightError(drawerIssue.id)">{{ getInsightError(drawerIssue.id) }}</div>
          <div v-else-if="getIssueInsight(drawerIssue.id)" class="ai-insight-grid">
            <div class="report-issue-block"><span class="report-issue-block__label">问题含义</span><p>{{ getIssueInsight(drawerIssue.id).insight.meaning }}</p></div>
            <div class="report-issue-block"><span class="report-issue-block__label">影响分析</span><p>{{ getIssueInsight(drawerIssue.id).insight.impact }}</p></div>
            <div class="report-issue-block"><span class="report-issue-block__label">修复建议</span><p>{{ getIssueInsight(drawerIssue.id).insight.fix }}</p></div>
            <div class="report-issue-block"><span class="report-issue-block__label">修复后验证</span><p>{{ getIssueInsight(drawerIssue.id).insight.verify }}</p></div>
          </div>
        </div>
      </template>
    </IssueDrawer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  cancelTask,
  downloadDastReport,
  downloadScaReport,
  downloadSastReport,
  exportDastReport,
  exportScaReport,
  exportSastReport,
  generateIssueInsight,
  getDastTask,
  getScaTask,
  getSastTask,
  rerunTask,
} from "../api/task";
import { getCurrentUser } from "../api/auth";
import type { Task } from "../types/task";
import ReportHero from "../components/report/ReportHero.vue";
import ActionBanner from "../components/report/ActionBanner.vue";
import SeverityTileGrid from "../components/report/SeverityTileGrid.vue";
import IssueTable from "../components/report/IssueTable.vue";
import IssueDrawer from "../components/report/IssueDrawer.vue";
import AdvicePanel from "../components/report/AdvicePanel.vue";
import OwaspRadarChart from "../components/report/charts/OwaspRadarChart.vue";
import SeverityDonutChart from "../components/report/charts/SeverityDonutChart.vue";
import FileTreemapChart from "../components/report/charts/FileTreemapChart.vue";
import {
  severityLabel,
  confidenceLabel,
  dastCategoryLabel,
  sastRuleLabel,
  owaspLabel,
} from "../utils/report-labels";

const route = useRoute();
const router = useRouter();
const task = ref<Task | null>(null);
const isAdminUser = ref(false);
const displayTaskNo = computed(() => task.value?.user_task_no || task.value?.id || "-");
const result = ref<any>(null);
const analysis = ref<any>(null);
const issues = ref<any[]>([]);
const errorMessage = ref("");
const actionMessage = ref("");
const issueInsights = ref<Record<number, any>>({});
const insightLoading = ref<Record<number, boolean>>({});
const insightError = ref<Record<number, string>>({});
let timer: number | null = null;

const canCancel = computed(() => Boolean(task.value && ["PENDING", "RUNNING"].includes(task.value.status)));
const canDownloadReport = computed(() => Boolean(task.value?.status === "SUCCESS" && task.value?.report_path));
const canReviewResult = computed(() => Boolean(task.value?.status === "SUCCESS" && (result.value || issues.value.length)));
const isDastReport = computed(() => task.value?.task_type === "DAST");
const isSastReport = computed(() => task.value?.task_type === "SAST");
const isScaReport = computed(() => task.value?.task_type === "SCA");
const isFromAdmin = computed(() => route.query.from === "admin");
const showAdminReturn = computed(() => canReviewResult.value && (isFromAdmin.value || isAdminUser.value));
const showScannerEngine = computed(() => Boolean(isSastReport.value && task.value?.scanner_engine));
const scannerEngineLabel = computed(() => {
  if (task.value?.scanner_engine === "semgrep") return "Semgrep";
  if (task.value?.scanner_engine === "bandit") return "Bandit";
  return "-";
});
const sastEngineTitleHint = computed(() => {
  if (!isSastReport.value) return "";
  if (task.value?.scanner_engine === "semgrep") return "规则驱动扫描";
  if (task.value?.scanner_engine === "bandit") return "Python 定向审计";
  return "静态代码审计";
});
const sastEngineSubtitleHint = computed(() => {
  if (!isSastReport.value) return "";
  if (task.value?.scanner_engine === "semgrep") return "当前结果更适合围绕规则命中、CWE/OWASP 映射和代码片段展开说明。";
  if (task.value?.scanner_engine === "bandit") return "当前结果更适合围绕 Python 典型编码风险和重点文件整改展开说明。";
  return "当前结果适合围绕规则命中、重点文件和整改优先级展开说明。";
});
const currentTargetLabel = computed(() => displayTargetName.value || result.value?.target_url || task.value?.target_url || task.value?.task_name || "-");
const displayTargetName = computed(() => {
  const raw = task.value?.target_name || "";
  return formatDisplayTargetName(raw) || raw || "-";
});
const statusTone = computed(() => {
  switch (task.value?.status) {
    case "RUNNING":
      return { label: "执行中", description: "任务正在运行，建议先关注状态变化，报告完成后再继续下钻。", className: "detail-status-card--running" };
    case "PENDING":
      return { label: "排队中", description: "任务已创建，正在等待系统调度执行。", className: "detail-status-card--pending" };
    case "SUCCESS":
      return { label: "已完成", description: "任务执行完成，可以直接查看风险分布、AI 解读和导出结果。", className: "detail-status-card--success" };
    case "FAILED":
      return { label: "执行失败", description: "本次任务未成功完成，建议先查看错误信息，再决定是否重新执行。", className: "detail-status-card--danger" };
    case "TIMEOUT":
      return { label: "已超时", description: "任务执行超出时限，建议调整配置后重新提交。", className: "detail-status-card--warning" };
    case "CANCELLED":
      return { label: "已取消", description: "任务已被取消，可按需要重新发起扫描。", className: "detail-status-card--warning" };
    default:
      return { label: "待确认", description: "任务状态等待同步，请先刷新查看最新结果。", className: "detail-status-card--pending" };
  }
});
const detailHeadline = computed(() => {
  const title = `${task.value?.task_name || "未命名任务"} 的执行结果`;
  if (isScaReport.value) return `${title} · 依赖组件审计`;
  if (!isSastReport.value) return title;
  return `${title} · ${sastEngineTitleHint.value}`;
});
const detailSubline = computed(() => {
  if (!task.value) return "";
  if (task.value.status === "SUCCESS") {
    if (isSastReport.value) {
      const base = sastExecutiveConclusion.value;
      return `${base} ${sastEngineSubtitleHint.value}`.trim();
    }
    if (isScaReport.value) return task.value.result_summary || scaExecutiveConclusion.value;
    return task.value.result_summary || (task.value.task_type === "DAST" ? dastExecutiveConclusion.value : sastExecutiveConclusion.value);
  }
  if (task.value.status === "FAILED") {
    return task.value.error_message || "任务执行失败，建议先复核目标配置、扫描范围和后端日志。";
  }
  if (task.value.status === "TIMEOUT") {
    return "任务执行超时，可以适当放宽超时时间或缩小扫描范围后重新尝试。";
  }
  if (task.value.status === "CANCELLED") {
    return "任务已取消，如需继续处理，可重新发起同类扫描。";
  }
  return "任务正在处理中，先关注执行状态和目标信息，报告生成后会自动更新。";
});
const autoRefreshHint = computed(() => canCancel.value ? "任务执行中，页面每 4 秒自动刷新一次状态。" : "");
const detailHeroBadge = computed(() => {
  if (isDastReport.value) return "Runtime Review";
  if (isSastReport.value) return "Code Review";
  if (isScaReport.value) return "Dependency Review";
  return "Task Review";
});
const detailHeroHighlights = computed(() => {
  if (!task.value) return [];
  const items: string[] = [`任务 #${displayTaskNo.value}`];
  if (showScannerEngine.value) items.push(`扫描引擎 ${scannerEngineLabel.value}`);
  if (task.value.started_at) {
    items.push(`开始时间 ${formatDateTime(task.value.started_at)}`);
  } else {
    items.push(`创建时间 ${formatDateTime(task.value.created_at)}`);
  }
  return items;
});
const primaryAction = computed(() => {
  if (canReviewResult.value) {
    if ((issues.value?.length || 0) > 0) {
      return {
        key: "issues",
        title: "先看漏洞与证据",
        detail: isDastReport.value
          ? "先看重点漏洞、请求证据和风险等级，再决定是否导出或复测。"
          : isScaReport.value
            ? "先看漏洞依赖、可修复版本和升级建议，再决定是否导出或复测。"
            : "先看高危规则、命中文件和整改建议，再决定是否导出或复测。"
      };
    }
    return {
      key: "report",
      title: "先看报告结论",
      detail: "本次任务已完成，优先阅读结论摘要和风险分布，再决定是否导出留档。"
    };
  }

  if (canCancel.value) {
    return {
      key: "refresh",
      title: "先观察执行状态",
      detail: "当前任务仍在运行或排队中，先刷新状态，等结果稳定后再进入报告阅读。"
    };
  }

  return {
    key: "rerun",
    title: "先复核后重跑",
    detail: "当前更适合先看失败或超时原因，确认配置无误后再重新执行任务。"
  };
});
const detailActions = computed(() => {
  const actions: Array<{ key: string; label: string; primary: boolean; handler: () => void }> = [];

  if (primaryAction.value.key === "report") {
    actions.push({ key: "report", label: "查看报告", primary: true, handler: scrollToReport });
  } else if (primaryAction.value.key === "issues") {
    actions.push({ key: "issues", label: "查看漏洞", primary: true, handler: scrollToIssues });
  } else if (primaryAction.value.key === "rerun") {
    actions.push({ key: "rerun-primary", label: "重新执行", primary: true, handler: rerunCurrentTask });
  } else {
    actions.push({ key: "refresh-primary", label: "刷新状态", primary: true, handler: loadDetail });
  }

  if (canDownloadReport.value) {
    actions.push({ key: "rerun-secondary", label: "重新执行", primary: false, handler: rerunCurrentTask });
  }

  actions.push({ key: "refresh-secondary", label: "刷新状态", primary: false, handler: loadDetail });

  if (canCancel.value) {
    actions.push({ key: "cancel", label: "取消任务", primary: false, handler: cancelCurrentTask });
  }

  if (canDownloadReport.value) {
    actions.push({ key: "export-pdf", label: "导出 PDF", primary: false, handler: () => downloadRenderedReport("pdf") });
    actions.push({ key: "export-html", label: "导出 HTML", primary: false, handler: () => downloadRenderedReport("html") });
    actions.push({ key: "download-json", label: "下载 JSON", primary: false, handler: downloadReport });
  }

  return actions;
});
const typeEntries = computed(() => Object.entries(result.value?.type_distribution || {}));
const severityEntries = computed(() => Object.entries(result.value?.severity_distribution || {}));
const confidenceEntries = computed(() => Object.entries(result.value?.confidence_distribution || {}));
const fileEntries = computed(() => Object.entries(result.value?.file_distribution || {}));
const packageEntries = computed(() => Object.entries(result.value?.package_distribution || {}));
const highRiskCount = computed(() => (result.value?.severity_distribution?.HIGH || 0) + (result.value?.severity_distribution?.CRITICAL || 0));
const severityChart = computed(() => buildChartData(result.value?.severity_distribution || {}, 5));
const typeChart = computed(() => buildChartData(result.value?.type_distribution || {}, 6));
const confidenceChart = computed(() => buildChartData(result.value?.confidence_distribution || {}, 5));
const fileChart = computed(() => buildChartData(result.value?.file_distribution || {}, 6));
const packageChart = computed(() => buildChartData(result.value?.package_distribution || {}, 6));
const topTypeLabel = computed(() => typeChart.value[0]?.label || "-");
const topFileLabel = computed(() => fileChart.value[0]?.label || "-");
const topPackageLabel = computed(() => packageChart.value[0]?.label || "-");
const highConfidenceCount = computed(() => result.value?.confidence_distribution?.HIGH || 0);
const owaspChart = computed(() => {
  const dist = analysis.value?.owasp_distribution || [];
  return dist.slice(0, 6);
});

const reportHeroBadge = computed(() => {
  if (isDastReport.value) return "Attack Surface";
  if (isSastReport.value) return "Code Risk";
  if (isScaReport.value) return "Dependency Risk";
  return "Security Review";
});
const reportHeroHighlights = computed(() => {
  if (!task.value) return [];
  return [`任务 #${displayTaskNo.value}`];
});
const riskTone = computed(() => {
  const critical = result.value?.severity_distribution?.CRITICAL || 0;
  const high = result.value?.severity_distribution?.HIGH || 0;
  const medium = result.value?.severity_distribution?.MEDIUM || 0;
  if (critical > 0) return { label: "严重", description: "存在需要立即处理的高影响安全问题。", className: "risk-critical" };
  if (high > 0) return { label: "高", description: "已发现高风险问题，建议优先整改。", className: "risk-high" };
  if (medium > 0) return { label: "中", description: "存在中等风险问题，应纳入近期修复计划。", className: "risk-medium" };
  if ((result.value?.issue_count || 0) > 0) return { label: "低", description: "以低风险暴露项为主，可作为安全基线说明。", className: "risk-low" };
  return { label: "清洁", description: "当前未检出明显漏洞项。", className: "risk-clean" };
});

const scaExecutiveConclusion = computed(() => {
  const target = displayTargetName.value || "依赖清单";
  const total = result.value?.vulnerability_count ?? 0;
  const fixable = result.value?.fixable_count ?? 0;
  if (total > 0) return `${target} 共识别 ${total} 个依赖漏洞，其中 ${fixable} 个存在可修复版本，建议优先升级可修复组件。`;
  return `${target} 未发现已知依赖漏洞，可作为当前组件安全基线。`;
});

const scaRecommendations = computed(() => {
  if (!issues.value.length) return ["保留当前依赖基线，并在版本升级或发布前重新执行 SCA。"];
  const recommendations = ["优先升级存在 fix_versions 的依赖包，升级后重新执行 SCA 复测。"];
  if (packageChart.value[0]) recommendations.push(`重点处理漏洞最集中的 ${packageChart.value[0].label}，减少重复风险来源。`);
  recommendations.push("将 requirements.txt 纳入发布前检查，保证依赖风险变化可追踪。");
  return recommendations;
});

const dastExecutiveConclusion = computed(() => {
  const target = result.value?.target_url || task.value?.target_url || "目标系统";
  const total = result.value?.issue_count ?? 0;
  const high = highRiskCount.value;
  if (high > 0) return `${target} 共发现 ${total} 个漏洞项，其中高风险 ${high} 个，建议优先整改高风险问题。`;
  if (total > 0) return `${target} 共发现 ${total} 个漏洞项，当前整体风险等级为${riskTone.value.label}。`;
  return `${target} 未发现明显漏洞项，可作为阶段性安全基线。`;
});

const dastExecutiveSubtitle = computed(() => {
  if (highRiskCount.value > 0) return "本次结果显示目标系统仍存在需要优先处置的运行态安全暴露面，建议先处理高影响问题，再完成安全头与配置层面的系统化加固。";
  if ((result.value?.issue_count || 0) > 0) return "本次结果以基线加固类问题为主，适合从传输安全、浏览器安全头和页面防护配置三个方向推进整改。";
  return "当前未发现明显漏洞项，可将本次结果作为后续复测和对比分析的安全基线。";
});

const sastExecutiveConclusion = computed(() => {
  const target = displayTargetName.value || "代码目标";
  const total = result.value?.issue_count ?? 0;
  const high = result.value?.severity_distribution?.HIGH || 0;
  if (high > 0) return `${target} 共识别 ${total} 个问题，其中高危 ${high} 个，建议优先处理高危与高置信度项。`;
  if (total > 0) return `${target} 共识别 ${total} 个问题，当前以中低风险和基线规则问题为主。`;
  return `${target} 未发现明显安全问题，可作为当前代码基线。`;
});

const sastExecutiveSubtitle = computed(() => {
  if ((result.value?.severity_distribution?.HIGH || 0) > 0) {
    return `本次结果表明代码层面存在高优先级安全问题，建议先修复高危项，再按文件集中区域和规则类型进行系统化治理。${sastEngineSubtitleHint.value}`;
  }
  if ((result.value?.issue_count || 0) > 0) {
    return `本次结果以规则命中和安全编码基线问题为主，适合从高频规则、重点文件和高置信度问题三个方向推进整改。${sastEngineSubtitleHint.value}`;
  }
  return `当前未发现明显问题，可将本次结果作为后续功能迭代后的静态审计对照基线。${sastEngineSubtitleHint.value}`;
});
const dastFindings = computed(() => {
  const findings: string[] = [];
  const total = result.value?.issue_count || 0;
  if (total > 0) findings.push(`本次动态扫描共识别 ${total} 个漏洞项，说明目标系统仍存在可被运行态访问与验证的安全暴露面。`);
  const topType = typeChart.value[0];
  if (topType) findings.push(`从漏洞类型分布看，当前最主要的问题类别为“${topType.label}”，占比约 ${topType.percent}%，表明该类安全控制缺失最为集中。`);
  if ((result.value?.crawled_pages || 0) > 0) findings.push(`扫描过程中共爬取 ${result.value.crawled_pages} 个页面或入口，结果能够反映当前测试范围内的主要运行态风险。`);
  if ((result.value?.anomaly_count || 0) > 0 || (result.value?.additional_count || 0) > 0) findings.push(`除明确漏洞外，扫描器还记录了 ${result.value?.anomaly_count || 0} 项异常与 ${result.value?.additional_count || 0} 项附加发现，可作为后续复测和人工验证的补充线索。`);
  if (!findings.length) findings.push("当前扫描未发现明确漏洞项，可将本次结果作为后续加固后对比复测的基线记录。");
  return findings;
});

const dastRecommendations = computed(() => {
  const recommendations: string[] = [];
  if (hasDastCategory(["Unencrypted Channels"])) recommendations.push("优先完成 HTTPS 全站启用、80 端口跳转与 HSTS 配置，避免页面与接口在传输过程中以明文方式暴露。");
  if (hasDastCategory(["Clickjacking Protection"])) recommendations.push("为核心页面补充 X-Frame-Options 或 CSP frame-ancestors 策略，防止页面被第三方站点嵌入利用。");
  if (hasDastCategory(["MIME Type Confusion"])) recommendations.push("为静态资源与接口响应补充准确的 Content-Type 与 X-Content-Type-Options: nosniff，降低浏览器错误解析风险。");
  if (highRiskCount.value > 0) recommendations.push("对高风险问题优先安排立即整改与复测，确保在论文演示或系统验收前完成高影响项闭环处理。");
  if (!recommendations.length) recommendations.push("继续保持当前安全配置，并在功能更新后执行复测，确认新增页面与接口未引入新的暴露面。");
  return recommendations;
});

const dastPriority = computed(() => {
  const priorities: Array<{ title: string; detail: string }> = [];
  if (hasDastCategory(["Unencrypted Channels"]) || highRiskCount.value > 0) priorities.push({ title: "第一优先级：先处理高影响暴露面", detail: "优先关闭明文传输、高风险接口暴露或可直接影响数据传输安全的问题，先降整体风险，再进入常规加固阶段。" });
  if (hasDastCategory(["Clickjacking Protection", "MIME Type Confusion"])) priorities.push({ title: "第二优先级：补齐浏览器侧安全防护", detail: "针对安全响应头、资源解析策略和页面防嵌套控制进行统一加固，这类问题通常集中且适合成批修复。" });
  priorities.push({ title: "第三优先级：完成复测与基线固化", detail: "整改后重新执行 DAST，保留对比结果，并将有效配置沉淀为系统默认安全基线，形成完整整改闭环。" });
  return priorities;
});

const dastTimeline = computed(() => {
  const steps: Array<{ phase: string; title: string; summary: string; items: string[] }> = [];
  if (hasDastCategory(["Unencrypted Channels"]) || highRiskCount.value > 0) steps.push({ phase: "P1", title: "立即处置高影响风险", summary: "优先修复直接影响传输安全或已进入高风险等级的问题，先压降整体暴露面。", items: ["关闭明文传输或高风险暴露点", "优先完成高影响问题复测", "确认核心接口已退出高风险状态"] });
  if (hasDastCategory(["Clickjacking Protection", "MIME Type Confusion"]) || (result.value?.issue_count || 0) > 0) steps.push({ phase: "P2", title: "短期完成配置与策略加固", summary: "补充浏览器安全头、页面嵌入限制和内容类型保护，提升前端访问面的整体防护能力。", items: ["补齐 Clickjacking 防护头", "修正 MIME 类型与 nosniff 策略", "统一页面与静态资源安全配置"] });
  steps.push({ phase: "P3", title: "复测验证并形成安全基线", summary: "在整改后重新扫描，记录结果变化并输出可用于论文展示的整改前后对比结论。", items: ["保留整改前后扫描结果", "整理结论用于论文展示", "将有效配置沉淀为安全基线"] });
  return steps;
});

const dastSharpConclusion = computed(() => {
  const total = result.value?.issue_count ?? 0;
  const high = highRiskCount.value;
  const pages = result.value?.crawled_pages ?? 0;
  if (total === 0) return "本次扫描未发现任何漏洞，目标当前外部攻击面良好。";
  if (high > 0) return `发现 ${total} 个漏洞，其中 ${high} 个高危/严重需立即处置 · 共爬取 ${pages} 个页面`;
  return `发现 ${total} 个漏洞，均为中低风险 · 共爬取 ${pages} 个页面`;
});

const dastSecondaryMetrics = computed<string[]>(() => {
  if (!result.value) return [];
  const items: string[] = [];
  items.push(`漏洞总数 ${result.value.issue_count ?? 0}`);
  if (typeof result.value.anomaly_count === "number") items.push(`异常项 ${result.value.anomaly_count}`);
  if (typeof result.value.crawled_pages === "number") items.push(`爬取页面 ${result.value.crawled_pages}`);
  return items;
});

const dastTopRiskTypeHint = computed(() => {
  const highIssues = issues.value.filter((i: any) => {
    const lvl = (i.level || "").toUpperCase();
    return lvl === "HIGH" || lvl === "CRITICAL";
  });
  if (!highIssues.length) return "建议尽快定位并修复，避免被进一步利用。";
  const catCounts: Record<string, number> = {};
  highIssues.forEach((i: any) => {
    const c = i.category || "未分类";
    catCounts[c] = (catCounts[c] || 0) + 1;
  });
  const top = Object.entries(catCounts).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([c]) => dastCategoryLabel(c));
  return `建议优先处理：${top.join("、")}`;
});

const dastHeroPills = computed<string[]>(() => {
  if (!result.value || !task.value) return [];
  return [
    `扫描目标：${result.value.target_url || task.value.target_url || "-"}`,
    `任务状态：${task.value.status}`,
    `扫描范围：${result.value.scan_scope || "-"}`,
    `总耗时：${formatDuration(task.value.duration_ms)}`,
  ];
});

const dastHeroMeta = computed<string[]>(() => [
  ...reportHeroHighlights.value,
  ...dastSecondaryMetrics.value,
]);

const dastIssueColumns: any[] = [
  { key: "__severity__", label: "等级", sortable: true },
  {
    key: "category",
    label: "漏洞类型",
    sortable: true,
    cellClass: "text-wrap",
    render: (issue: any) => dastCategoryLabel(issue.category),
  },
  { key: "method", label: "方法" },
  { key: "path", label: "路径", cellClass: "text-wrap dast-cell-path" },
  { key: "owasp", label: "OWASP", render: (issue: any) => owaspLabel(issue.owasp) },
  { key: "__action__", label: "" },
];

const dastIssueFilter = {
  severityField: "level",
  categoryField: "category",
  searchFields: ["path", "parameter"],
  searchPlaceholder: "搜索路径或参数...",
};

const dastAdviceTabs = computed<any[]>(() => [
  {
    key: "analysis",
    label: "风险分析",
    content: { type: "mixed", intro: dastExecutiveConclusion.value, items: dastFindings.value },
  },
  {
    key: "fix",
    label: "整改建议",
    content: { type: "list", items: dastRecommendations.value },
  },
  {
    key: "priority",
    label: "处置顺序",
    content: { type: "ordered", items: dastPriority.value, dangerFirst: true },
  },
  {
    key: "timeline",
    label: "优先级时间线",
    content: { type: "timeline", steps: dastTimeline.value },
  },
]);

const drawerIssue = ref<any>(null);
const drawerOpen = computed(() => drawerIssue.value !== null);

const drawerLevel = computed(() => {
  if (!drawerIssue.value) return "";
  return (
    drawerIssue.value.level ||
    drawerIssue.value.issue_severity ||
    drawerIssue.value.severity ||
    "UNKNOWN"
  );
});

const drawerTitle = computed(() => {
  if (!drawerIssue.value) return "";
  if (isDastReport.value) return drawerIssue.value.category || "未命名漏洞项";
  if (isSastReport.value) return drawerIssue.value.test_name || drawerIssue.value.test_id || "未命名规则";
  if (isScaReport.value) {
    const name = drawerIssue.value.package_name || "";
    const ver = drawerIssue.value.installed_version || "";
    const combined = `${name}${ver ? " " + ver : ""}`.trim();
    return combined || "依赖漏洞";
  }
  return "";
});

const drawerSubtitle = computed(() => {
  if (!drawerIssue.value) return "";
  if (isDastReport.value) {
    return `${drawerIssue.value.method || "-"} · ${drawerIssue.value.path || "-"} · 参数 ${drawerIssue.value.parameter || "无"}`;
  }
  if (isSastReport.value) return getSastIssueEvidence(drawerIssue.value);
  if (isScaReport.value) return drawerIssue.value.vulnerability_id || "-";
  return "";
});

const drawerEvidenceText = computed(() => {
  if (!drawerIssue.value) return "";
  if (isDastReport.value) return drawerIssue.value.curl_command || drawerIssue.value.http_request || "";
  if (isSastReport.value) return drawerIssue.value.code || "";
  return "";
});

const drawerEvidenceLabel = computed(() => {
  if (isDastReport.value) return "查看请求证据";
  if (isSastReport.value) return "查看代码证据";
  return "查看证据";
});

function openIssueDrawer(issue: any) {
  drawerIssue.value = issue;
  if (issue?.id) void loadIssueInsight(issue.id);
}

function closeIssueDrawer() {
  drawerIssue.value = null;
}

const sastFindings = computed(() => {
  const findings: string[] = [];
  const total = result.value?.issue_count || 0;
  if (total > 0) findings.push(`本次静态审计共识别 ${total} 个问题，说明目标代码中存在可由规则检测到的安全编码隐患。`);
  const topRule = typeChart.value[0];
  if (topRule) findings.push(`从规则分布看，当前命中最多的规则为“${topRule.label}”，占比约 ${topRule.percent}%，说明该类编码问题最为集中。`);
  const topFile = fileChart.value[0];
  if (topFile) findings.push(`从文件分布看，问题主要集中在 ${topFile.label}，该文件应作为优先审查和整改对象。`);
  const highConfidence = result.value?.confidence_distribution?.HIGH || 0;
  if (highConfidence > 0) findings.push(`当前存在 ${highConfidence} 条高置信度问题，这类结果更值得优先人工复核和修复。`);
  if (!findings.length) findings.push("当前静态审计未发现明确问题，可将本次结果作为后续代码变更对比的安全基线。");
  return findings;
});

const sastRecommendations = computed(() => {
  const recommendations: string[] = [];
  if ((result.value?.severity_distribution?.HIGH || 0) > 0) recommendations.push("优先修复高危问题和高置信度问题，先消除影响面较大的代码风险，再进入常规规则治理阶段。");
  if (typeChart.value[0]) recommendations.push(`针对高频规则“${getSastRuleLabel(typeChart.value[0].label)}”梳理统一整改模式，避免逐条修复导致工作量分散。`);
  if (fileChart.value[0]) recommendations.push(`优先审查问题集中的文件 ${fileChart.value[0].label}，通过集中修复提高整改效率。`);
  recommendations.push("整改后重新执行 SAST，确认同类规则不再重复命中，并将修复经验沉淀为编码规范或审计清单。");
  return recommendations;
});

const sastPriority = computed(() => {
  const priorities: Array<{ title: string; detail: string }> = [];
  if ((result.value?.severity_distribution?.HIGH || 0) > 0) priorities.push({ title: "第一优先级：先处理高危与高置信度问题", detail: "优先修复影响面更大的高危问题和工具判断更明确的高置信度问题，先降低代码层面的核心风险。" });
  if (fileChart.value.length > 0 || typeChart.value.length > 0) priorities.push({ title: "第二优先级：按高频规则和重点文件集中治理", detail: "针对命中最多的规则类型和问题最集中的文件建立批量修复策略，提高整改效率和一致性。" });
  priorities.push({ title: "第三优先级：复测与规范固化", detail: "完成修复后重新扫描，并将有效整改方案沉淀为编码规范、检查清单或开发自检要求。" });
  return priorities;
});

const sastTimeline = computed(() => {
  const steps: Array<{ phase: string; title: string; summary: string; items: string[] }> = [];
  if ((result.value?.severity_distribution?.HIGH || 0) > 0) steps.push({ phase: "P1", title: "优先修复高危问题", summary: "先处理高危和高置信度问题，尽快降低核心代码风险。", items: ["定位高危规则命中位置", "完成人工复核与代码修复", "确认相关调用链不再存在同类隐患"] });
  steps.push({ phase: "P2", title: "按规则与文件集中整改", summary: "针对高频规则和重点文件执行成批治理，提升整改效率。", items: ["按规则归类问题", "聚焦问题最集中的文件", "统一修复模式减少重复劳动"] });
  steps.push({ phase: "P3", title: "复测并固化安全基线", summary: "通过复测验证整改效果，并将结果沉淀为长期可复用的开发规范。", items: ["重新执行 SAST 复测", "对比整改前后结果", "更新编码规范与检查清单"] });
  return steps;
});

function buildChartData(source: Record<string, number>, limit = 6) {
  const entries = Object.entries(source || {}).sort((a, b) => Number(b[1]) - Number(a[1])).slice(0, limit);
  const total = entries.reduce((sum, [, count]) => sum + Number(count || 0), 0) || 1;
  return entries.map(([label, count]) => ({ label, count: Number(count || 0), percent: Math.round((Number(count || 0) / total) * 100) }));
}

function severityToneClass(label?: string) {
  if (!label) return "";
  const value = label.toUpperCase();
  if (value.includes("CRITICAL") || value.includes("HIGH")) return "is-danger";
  if (value.includes("MEDIUM")) return "is-warning";
  if (value.includes("LOW")) return "is-info";
  return "";
}
function hasDastCategory(names: string[]) {
  return issues.value.some((item) => names.includes(item.category));
}

function getDastIssueSummary(issue: any) {
  const category = issue?.category || "";
  if (category === "Unencrypted Channels") return "检测到目标站点存在未加密传输通道，部分页面或接口可能仍通过明文方式传输数据。";
  if (category === "Clickjacking Protection") return "检测到页面缺少点击劫持防护配置，页面可能被第三方站点嵌入利用。";
  if (category === "MIME Type Confusion") return "检测到响应内容类型控制不足，浏览器可能对资源类型做不安全的自动推断。";
  if (category) return `检测到“${category}”相关安全问题，说明目标系统在当前扫描范围内存在对应防护缺口。`;
  return "当前条目未返回标准化漏洞说明，但扫描结果提示该处存在需要关注的运行态安全问题。";
}
function getDastIssueImpact(issue: any) {
  const category = issue?.category || "";
  if (category === "Unencrypted Channels") return "目标站点存在明文传输暴露，攻击者可能在网络链路中窃取或篡改请求与响应内容。";
  if (category === "Clickjacking Protection") return "页面可被第三方站点嵌入，可能诱导用户在未知情况下完成敏感操作。";
  if (category === "MIME Type Confusion") return "浏览器可能对资源做错误解析，增加脚本或敏感内容被意外执行的风险。";
  return issue?.info || "该漏洞项说明目标系统在当前扫描路径下存在需要关注的运行态安全暴露面。";
}

function getDastIssueRecommendation(issue: any) {
  const category = issue?.category || "";
  if (category === "Unencrypted Channels") return "启用 HTTPS、配置 80 到 443 跳转，并增加 HSTS 头，确保页面与接口全程加密传输。";
  if (category === "Clickjacking Protection") return "为关键页面添加 X-Frame-Options 或 CSP frame-ancestors，限制页面被外站框架引用。";
  if (category === "MIME Type Confusion") return "修正响应 Content-Type，并补充 X-Content-Type-Options: nosniff，避免浏览器进行不安全的内容嗅探。";
  return "结合业务场景复核该问题影响范围，并在整改后重新发起扫描确认问题是否消除。";
}

function getDastIssueEvidence(issue: any) {
  if (issue?.path && issue?.method) return `${issue.method} ${issue.path}`;
  if (issue?.path) return issue.path;
  if (issue?.parameter) return `参数：${issue.parameter}`;
  return issue?.referer || "详见原始扫描报告中的请求与响应上下文。";
}

function getSastIssueSummary(issue: any) {
  const ruleId = String(issue?.test_id || "").toUpperCase();
  const ruleName = String(issue?.test_name || "");
  if (ruleId === "B602" || ruleName.includes("subprocess_popen_with_shell_equals_true")) return "检测到使用 shell=True 调用子进程，这种写法容易引入命令注入风险。";
  if (ruleId === "B301" || ruleName.includes("pickle")) return "检测到使用 pickle 进行反序列化，不可信输入可能触发任意代码执行。";
  if (ruleId === "B506" || ruleName.includes("yaml_load")) return "检测到使用不安全的 YAML 加载方式，外部输入可能触发非预期对象解析。";
  if (ruleId === "B324" || ruleName.includes("hashlib")) return "检测到使用弱哈希算法处理数据，安全强度不足，不能用于敏感场景。";
  if (ruleId === "B105" || ruleId === "B106" || ruleId === "B107") return "检测到代码中存在硬编码口令、密钥或令牌信息，这类敏感信息不应直接写入源码。";
  if (ruleId === "B501" || ruleName.includes("request_with_no_cert_validation")) return "检测到请求关闭了证书校验，通信过程容易受到中间人攻击影响。";
  if (ruleId === "B201" || ruleName.includes("flask_debug_true")) return "检测到 Flask 以调试模式运行，生产环境开启调试可能暴露更多敏感信息。";
  if (ruleId === "B608") return "检测到 SQL 语句可能通过字符串拼接构造，存在注入风险。";
  if (ruleName) return `检测到规则“${ruleName}”命中，说明代码中存在与该安全规则相关的不安全实现。`;
  return "当前条目命中了静态审计规则，说明代码中存在需要进一步人工复核的安全隐患。";
}
function getSastIssueImpact(issue: any) {
  const ruleId = String(issue?.test_id || "").toUpperCase();
  const ruleName = String(issue?.test_name || "");
  if (ruleId === "B602" || ruleName.includes("subprocess_popen_with_shell_equals_true")) return "如果外部输入进入命令拼接流程，攻击者可能借此执行任意系统命令，进一步影响主机和数据安全。";
  if (ruleId === "B301" || ruleName.includes("pickle")) return "一旦反序列化数据来自不可信来源，攻击者可能通过构造恶意对象执行任意代码，风险较高。";
  if (ruleId === "B506" || ruleName.includes("yaml_load")) return "不安全的 YAML 解析方式可能导致恶意对象被加载，进而影响程序执行安全和服务稳定性。";
  if (ruleId === "B324" || ruleName.includes("hashlib")) return "弱哈希算法容易被快速破解或碰撞，不适合用于口令保护、签名或敏感数据完整性校验。";
  if (ruleId === "B105" || ruleId === "B106" || ruleId === "B107") return "敏感凭据直接写入源码后，一旦代码泄露、共享或被提交到仓库，相关系统就会面临直接失陷风险。";
  if (ruleId === "B501" || ruleName.includes("request_with_no_cert_validation")) return "关闭证书校验会削弱 HTTPS 的保护能力，使通信链路更容易受到中间人攻击。";
  if (ruleId === "B201" || ruleName.includes("flask_debug_true")) return "调试模式可能暴露堆栈、配置或调试入口，增加敏感信息泄露和误用风险。";
  if (ruleId === "B608") return "SQL 通过字符串拼接构造时，外部输入可能直接影响查询逻辑，进而造成数据泄露、篡改甚至删除。";
  return "该问题反映出代码中存在不安全实现或潜在漏洞模式，若不修复，可能在运行时演化为可利用风险。";
}

function getSastIssueRecommendation(issue: any) {
  const ruleId = String(issue?.test_id || "").toUpperCase();
  const ruleName = String(issue?.test_name || "");
  if (ruleId === "B602" || ruleName.includes("subprocess_popen_with_shell_equals_true")) return "避免使用 shell=True 执行外部输入参与拼接的命令，改用参数化命令列表并严格校验输入内容。";
  if (ruleId === "B301" || ruleName.includes("pickle")) return "不要对不可信输入使用 pickle 反序列化，优先改用 JSON 等安全格式，或在来源可控前提下增加完整性校验。";
  if (ruleId === "B506" || ruleName.includes("yaml_load")) return "将不安全的 YAML 加载方式替换为安全加载接口，并限制可解析的数据类型。";
  if (ruleId === "B324" || ruleName.includes("hashlib")) return "将 MD5 等弱算法替换为更安全的哈希方案；若用于口令处理，应使用专门的密码散列算法。";
  if (ruleId === "B105" || ruleId === "B106" || ruleId === "B107") return "将硬编码的口令、密钥和令牌迁移到环境变量、配置中心或密钥管理服务中统一管理。";
  if (ruleId === "B501" || ruleName.includes("request_with_no_cert_validation")) return "开启证书校验并正确维护受信任证书链，避免在正式环境中关闭 TLS 验证。";
  if (ruleId === "B201" || ruleName.includes("flask_debug_true")) return "关闭生产环境调试模式，改用受控日志和错误处理机制替代调试输出。";
  if (ruleId === "B608") return "使用参数化查询或 ORM 提供的安全接口构造 SQL，避免将外部输入直接拼接到语句中。";
  return `建议围绕规则“${getSastRuleLabel(ruleName || ruleId)}”检查对应实现，并在修改后重新执行静态审计确认问题已消除。`;
}

function getSastRuleLabel(value: string) {
  const text = String(value || "");
  const upper = text.toUpperCase();
  if (upper === "B602" || text.includes("subprocess_popen_with_shell_equals_true")) return "shell=True 子进程调用风险";
  if (upper === "B301" || text.includes("pickle")) return "不安全反序列化风险";
  if (upper === "B506" || text.includes("yaml_load")) return "不安全 YAML 解析风险";
  if (upper === "B324" || text.includes("hashlib")) return "弱哈希算法使用风险";
  if (upper === "B105" || upper === "B106" || upper === "B107") return "硬编码敏感信息风险";
  if (upper === "B501" || text.includes("request_with_no_cert_validation")) return "TLS 证书校验关闭风险";
  if (upper === "B201" || text.includes("flask_debug_true")) return "Flask 调试模式暴露风险";
  if (upper === "B608") return "SQL 拼接注入风险";
  return text || "静态审计规则";
}
function getSastIssueEvidence(issue: any) {
  const file = issue?.filename || "未知文件";
  const line = issue?.line_number ? `:${issue.line_number}` : "";
  return `${file}${line}`;
}

function getScaIssueSummary(issue: any) {
  const pkg = issue?.package_name || "依赖包";
  const ver = issue?.installed_version || "未知版本";
  const desc = String(issue?.description || "").trim();
  if (desc) {
    const short = desc.length > 120 ? desc.slice(0, 120) + "…" : desc;
    return `${pkg} ${ver}：${short}`;
  }
  return `检测到 ${pkg} ${ver} 存在已知漏洞，建议升级到可修复版本后复测。`;
}

function getScaIssueImpact(issue: any) {
  const pkg = issue?.package_name || "依赖包";
  const aliases = Array.isArray(issue?.aliases) ? issue.aliases.filter(Boolean) : [];
  if (aliases.length) {
    return `该漏洞同时关联 ${aliases.slice(0, 3).join("、")} 等公开漏洞编号，存在被自动化扫描工具或攻击者直接定位的风险，建议尽快处置。`;
  }
  return `${pkg} 的当前版本存在已公开的安全漏洞，若被利用可能影响依赖该组件的功能与数据安全。`;
}

function getScaIssueRecommendation(issue: any) {
  const pkg = issue?.package_name || "依赖包";
  const fixVersions = Array.isArray(issue?.fix_versions) ? issue.fix_versions.filter(Boolean) : [];
  if (fixVersions.length) {
    return `升级 ${pkg} 到 ${fixVersions.slice(0, 3).join(" / ")}（任选其一）后重新执行 SCA 复测，确认问题已闭环。`;
  }
  return `当前尚无官方可修复版本，建议关注上游公告、评估降级或替代组件的可行性，并将该依赖纳入持续监控范围。`;
}

function getScaIssueEvidence(issue: any) {
  const vulnId = issue?.vulnerability_id || "";
  const aliases = Array.isArray(issue?.aliases) ? issue.aliases.filter(Boolean) : [];
  if (vulnId && aliases.length) return `${vulnId}（${aliases.slice(0, 3).join("、")}）`;
  if (vulnId) return vulnId;
  if (aliases.length) return aliases.slice(0, 3).join("、");
  return "详见原始扫描报告中的漏洞条目。";
}

const scaSharpConclusion = computed(() => {
  const total = result.value?.vulnerability_count ?? 0;
  const fixable = result.value?.fixable_count ?? 0;
  const deps = result.value?.dependency_count ?? 0;
  if (total === 0) return `共扫描 ${deps} 个依赖，未发现已知漏洞，可作为当前组件安全基线。`;
  if (fixable > 0) return `发现 ${total} 个依赖漏洞，其中 ${fixable} 个存在可修复版本 · 共扫描 ${deps} 个依赖`;
  return `发现 ${total} 个依赖漏洞，暂无官方可修复版本 · 共扫描 ${deps} 个依赖`;
});

const sastSharpConclusion = computed(() => {
  const total = result.value?.issue_count ?? 0;
  const high = result.value?.severity_distribution?.HIGH || 0;
  const highConf = highConfidenceCount.value;
  if (total === 0) return "本次静态审计未发现明显问题，可作为当前代码基线。";
  if (high > 0) return `识别 ${total} 个问题，其中 ${high} 个高危 · 高置信度 ${highConf} 条`;
  return `识别 ${total} 个问题，以中低风险和基线规则为主 · 高置信度 ${highConf} 条`;
});

const scaHeroPills = computed<string[]>(() => {
  if (!task.value) return [];
  return [
    `依赖清单：${displayTargetName.value}`,
    `任务状态：${task.value.status}`,
    `创建时间：${formatDateTime(task.value.created_at)}`,
    `总耗时：${formatDuration(task.value.duration_ms)}`,
  ];
});

const scaHeroMeta = computed<string[]>(() => {
  if (!result.value) return [];
  const items: string[] = [];
  items.push(`依赖总数 ${result.value.dependency_count ?? 0}`);
  items.push(`可修复项 ${result.value.fixable_count ?? 0}`);
  if (topPackageLabel.value && topPackageLabel.value !== "-") {
    items.push(`重点包 ${topPackageLabel.value}`);
  }
  return items;
});

const scaHighRiskCount = computed(() => {
  return issues.value.filter((i: any) => {
    const lvl = (i.severity || "").toUpperCase();
    return lvl === "HIGH" || lvl === "CRITICAL";
  }).length;
});

const scaTopRiskHint = computed(() => {
  const highIssues = issues.value.filter((i: any) => {
    const lvl = (i.severity || "").toUpperCase();
    return lvl === "HIGH" || lvl === "CRITICAL";
  });
  if (!highIssues.length) return "建议持续关注新公布的依赖漏洞。";
  const fixable = highIssues.filter((i: any) => Array.isArray(i.fix_versions) && i.fix_versions.length).length;
  if (fixable > 0) return `其中 ${fixable} 个已存在可修复版本，建议优先升级。`;
  const pkgs = Array.from(new Set(highIssues.map((i: any) => i.package_name).filter(Boolean))).slice(0, 3);
  return `集中在依赖：${pkgs.join("、") || "见漏洞清单"}`;
});

const scaIssueColumns: any[] = [
  { key: "__severity__", label: "等级", sortable: true },
  { key: "package_name", label: "依赖包", sortable: true, cellClass: "text-wrap" },
  { key: "installed_version", label: "当前版本" },
  {
    key: "fix_versions",
    label: "可修复版本",
    cellClass: "text-wrap",
    render: (issue: any) => Array.isArray(issue.fix_versions) && issue.fix_versions.length ? issue.fix_versions.slice(0, 2).join(", ") : "—",
  },
  { key: "vulnerability_id", label: "漏洞编号", cellClass: "dast-cell-path" },
  { key: "__action__", label: "" },
];

const scaIssueFilter = {
  severityField: "severity",
  categoryField: "package_name",
  searchFields: ["package_name", "vulnerability_id", "description"],
  categoryLabel: "全部依赖包",
  searchPlaceholder: "搜索包名、漏洞编号或描述...",
};

const scaAdviceTabs = computed<any[]>(() => [
  {
    key: "analysis",
    label: "风险分析",
    content: { type: "mixed", intro: scaExecutiveConclusion.value },
  },
  {
    key: "fix",
    label: "整改建议",
    content: { type: "list", items: scaRecommendations.value },
  },
]);

const sastHeroPills = computed<string[]>(() => {
  if (!task.value) return [];
  return [
    `扫描目标：${displayTargetName.value}`,
    `任务状态：${task.value.status}`,
    `创建时间：${formatDateTime(task.value.created_at)}`,
    `总耗时：${formatDuration(task.value.duration_ms)}`,
  ];
});

const sastHeroMeta = computed<string[]>(() => {
  if (!result.value) return [];
  const items = [...reportHeroHighlights.value];
  items.push(`问题总数 ${result.value.issue_count ?? 0}`);
  items.push(`高置信度 ${highConfidenceCount.value}`);
  if (topTypeLabel.value && topTypeLabel.value !== "-") {
    items.push(`重点规则 ${topTypeLabel.value}`);
  }
  return items;
});

const sastHighRiskCount = computed(() => result.value?.severity_distribution?.HIGH || 0);

const sastTopRiskHint = computed(() => {
  const top = typeChart.value[0];
  if (top) return `集中在规则：${sastRuleLabel(top.label)}（占比约 ${top.percent}%）`;
  return "建议尽快人工复核高危规则命中位置。";
});

const sastIssueColumns: any[] = [
  { key: "__severity__", label: "等级", sortable: true },
  {
    key: "rule",
    label: "规则",
    sortable: true,
    cellClass: "text-wrap",
    render: (issue: any) => {
      const id = issue.test_id || "";
      const name = issue.test_name || "";
      const combined = id ? `${id}:${name}` : name;
      return combined ? sastRuleLabel(combined) : "未命名规则";
    },
  },
  { key: "issue_confidence", label: "置信度", render: (issue: any) => confidenceLabel(issue.issue_confidence) },
  {
    key: "location",
    label: "位置",
    cellClass: "text-wrap dast-cell-path",
    render: (issue: any) => getSastIssueEvidence(issue),
  },
  { key: "cwe", label: "CWE" },
  { key: "__action__", label: "" },
];

const sastIssueFilter = {
  severityField: "issue_severity",
  categoryField: "test_id",
  searchFields: ["filename", "test_name", "test_id", "code"],
  categoryLabel: "全部规则",
  searchPlaceholder: "搜索文件、规则或代码片段...",
};

const sastAdviceTabs = computed<any[]>(() => [
  {
    key: "analysis",
    label: "风险分析",
    content: { type: "mixed", intro: sastExecutiveConclusion.value, items: sastFindings.value },
  },
  {
    key: "fix",
    label: "整改建议",
    content: { type: "list", items: sastRecommendations.value },
  },
  {
    key: "priority",
    label: "处置顺序",
    content: { type: "ordered", items: sastPriority.value, dangerFirst: true },
  },
  {
    key: "timeline",
    label: "优先级时间线",
    content: { type: "timeline", steps: sastTimeline.value },
  },
]);


function getInsightSummary(issueId: number) {
  const insight = getIssueInsight(issueId)?.insight;
  if (!insight) return "";
  const meaning = String(insight.meaning || "").trim();
  const impact = String(insight.impact || "").trim();
  if (meaning && impact) {
    return `${meaning} ${impact}`;
  }
  return meaning || impact || "AI 已完成当前问题的增强解读。";
}function getIssueInsight(issueId: number) {
  return issueInsights.value[issueId] || null;
}

function isInsightLoading(issueId: number) {
  return Boolean(insightLoading.value[issueId]);
}

function getInsightError(issueId: number) {
  return insightError.value[issueId] || "";
}

async function loadIssueInsight(issueId: number) {
  if (!task.value || issueInsights.value[issueId] || insightLoading.value[issueId]) return;
  insightLoading.value = { ...insightLoading.value, [issueId]: true };
  insightError.value = { ...insightError.value, [issueId]: "" };
  try {
    const response = await generateIssueInsight({ task_id: task.value.id, issue_id: issueId });
    const payload = response?.data || {};
    issueInsights.value = { ...issueInsights.value, [issueId]: payload };
  } catch (error: any) {
    insightError.value = {
      ...insightError.value,
      [issueId]: error?.response?.data?.message || "AI 解读暂时不可用",
    };
  } finally {
    insightLoading.value = { ...insightLoading.value, [issueId]: false };
  }
}

function formatDuration(duration?: number | null) {
  if (!duration) return "-";
  if (duration < 1000) return `${duration} ms`;
  return `${(duration / 1000).toFixed(2)} s`;
}

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatDisplayTargetName(value?: string | null) {
  if (!value) return "";
  const normalized = String(value).split(/[\\/]/).pop() || String(value);
  const withoutPrefix = normalized.replace(/^[0-9a-f]{24,}-/i, "");
  return withoutPrefix || normalized;
}

function taskTypeClass(taskType?: Task["task_type"] | null) {
  if (taskType === "SAST") return "task-kind-badge--sast";
  if (taskType === "SCA") return "task-kind-badge--engine";
  return "task-kind-badge--dast";
}

function resolveTaskType(taskType?: string | null) {
  const value = String(taskType || "").toUpperCase();
  if (value === "DAST" || value === "SAST" || value === "SCA") return value as "DAST" | "SAST" | "SCA";
  return null;
}

function syncPolling(nextTask?: Task | null) {
  if (nextTask && ["PENDING", "RUNNING"].includes(nextTask.status)) {
    if (!timer) timer = window.setInterval(loadDetail, 4000);
  } else if (timer) {
    window.clearInterval(timer);
    timer = null;
  }
}

async function requestDetail(taskId: number, taskType: "DAST" | "SAST" | "SCA") {
  const response = taskType === "DAST"
    ? await getDastTask(taskId)
    : taskType === "SCA"
      ? await getScaTask(taskId)
      : await getSastTask(taskId);
  return { detail: response?.data || {}, taskType };
}

async function loadDetail() {
  errorMessage.value = "";
  const taskId = Number(route.params.id);
  if (!taskId) {
    errorMessage.value = "任务 ID 无效";
    return;
  }

  const candidates = [
    resolveTaskType(route.query.type as string | undefined),
    resolveTaskType(task.value?.task_type),
    "SAST",
    "SCA",
    "DAST"
  ].filter((value, index, array): value is "SAST" | "DAST" | "SCA" => Boolean(value) && array.indexOf(value) === index);

  let lastError: any = null;

  for (const taskType of candidates) {
    try {
      const { detail } = await requestDetail(taskId, taskType);
      if (detail?.task) {
        task.value = detail.task;
        result.value = detail.result || null;
        analysis.value = detail.analysis || null;
        issues.value = detail.issues || [];
        syncPolling(detail.task);
        return;
      }
    } catch (error: any) {
      lastError = error;
    }
  }

  syncPolling(null);
  errorMessage.value = lastError?.response?.data?.message || lastError?.message || "加载任务详情失败";
}

async function loadCurrentUserRole() {
  try {
    const response = await getCurrentUser();
    isAdminUser.value = response?.data?.user?.role === "admin";
  } catch {
    isAdminUser.value = false;
  }
}

async function cancelCurrentTask() {
  if (!task.value) return;
  actionMessage.value = "";
  try {
    const response = await cancelTask(task.value.id);
    actionMessage.value = response.message || "任务已取消";
    await loadDetail();
  } catch (error: any) {
    actionMessage.value = error?.response?.data?.message || "取消任务失败";
  }
}

async function rerunCurrentTask() {
  if (!task.value) return;
  actionMessage.value = "";
  try {
    const response = await rerunTask(task.value.id);
    actionMessage.value = response.message || "任务已重新提交";
    const newTaskId = response?.data?.new_task?.id;
    if (newTaskId) await router.push({ name: "task-detail", params: { id: newTaskId } });
    await loadDetail();
  } catch (error: any) {
    actionMessage.value = error?.response?.data?.message || "重跑任务失败";
  }
}


function scrollToBlock(id: string) {
  const node = document.getElementById(id);
  if (!node) return;
  node.scrollIntoView({ behavior: "smooth", block: "start" });
}

function scrollToReport() {
  scrollToBlock("detail-report");
}

function scrollToIssues() {
  scrollToBlock("detail-issues");
}

function goBackToList() {
  router.push("/admin");
}

async function downloadRenderedReport(format: "html" | "pdf") {
  if (!task.value) return;
  try {
    const blob = task.value.task_type === "DAST"
      ? await exportDastReport(task.value.id, format)
      : task.value.task_type === "SCA"
        ? await exportScaReport(task.value.id, format)
        : await exportSastReport(task.value.id, format);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${task.value.task_type?.toLowerCase() || "task"}_report_${displayTaskNo.value}.${format}`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (error: any) {
    actionMessage.value = error?.response?.data?.message || `导出${format.toUpperCase()}报告失败`;
  }
}

async function downloadReport() {
  if (!task.value) return;
  try {
    const blob = task.value.task_type === "DAST"
      ? await downloadDastReport(task.value.id)
      : task.value.task_type === "SCA"
        ? await downloadScaReport(task.value.id)
        : await downloadSastReport(task.value.id);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${task.value.task_type?.toLowerCase() || "task"}_${displayTaskNo.value}.json`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (error: any) {
    actionMessage.value = error?.response?.data?.message || "下载报告失败";
  }
}

onMounted(() => {
  void loadCurrentUserRole();
  loadDetail();
});

onUnmounted(() => {
  if (timer) {
    window.clearInterval(timer);
    timer = null;
  }
});
</script>



















<style scoped>
.detail-next-step {
  display: grid;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.16);
}

.detail-next-step__label {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(248, 251, 255, 0.72);
}

.detail-next-step strong {
  font-size: 24px;
  line-height: 1.2;
  color: #ffffff;
}

.detail-next-step p {
  margin: 0;
  color: rgba(248, 251, 255, 0.88);
  line-height: 1.7;
}

.detail-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.detail-facts span {
  border: 1px solid rgba(148, 254, 255, 0.18);
  border-radius: 14px;
  padding: 12px;
  background: rgba(9, 19, 34, 0.32);
  color: rgba(248, 251, 255, 0.9);
}

.report-return-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  margin-bottom: 12px;
  border: 0;
  padding: 0;
  color: rgba(248, 251, 255, 0.9);
  background: transparent;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}

.report-return-link:hover {
  color: #ffffff;
  text-decoration: underline;
}

.dast-cell-path {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: var(--ink-700, #49627d);
}
</style>
