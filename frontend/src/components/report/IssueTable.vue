<template>
  <div class="issue-table-block">
    <div class="issue-table-filter-bar" v-if="issues.length">
      <div class="issue-table-filter-bar__group">
        <span class="muted issue-table-filter-bar__label">严重度</span>
        <button
          v-for="level in SEVERITY_OPTIONS"
          :key="`chip-${level}`"
          type="button"
          class="severity-chip"
          :class="[
            `severity-chip--${level.toLowerCase()}`,
            { 'severity-chip--active': filterSeverities.includes(level) },
          ]"
          @click="toggleSeverityFilter(level)"
        >{{ severityLabel(level) }}</button>
      </div>
      <select
        v-if="categoryOptions.length"
        class="field-input issue-table-filter-bar__select"
        v-model="filterCategory"
      >
        <option value="">{{ filter.categoryLabel || '全部类别' }}</option>
        <option v-for="cat in categoryOptions" :key="cat" :value="cat">{{ cat }}</option>
      </select>
      <input
        v-if="filter.searchFields && filter.searchFields.length"
        class="field-input issue-table-filter-bar__search"
        type="search"
        :placeholder="filter.searchPlaceholder || '搜索...'"
        v-model="filterKeyword"
      />
      <button class="button secondary" type="button" @click="resetFilters">重置</button>
      <div class="issue-table-filter-bar__summary muted">
        共 {{ issues.length }} 条 · 当前显示 {{ filteredIssues.length }}
      </div>
    </div>

    <div class="issue-table-wrap" v-if="filteredIssues.length">
      <table class="table issue-table">
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="`th-${col.key}`"
              :class="{
                'issue-table__th-sort': col.sortable,
                'issue-table__th-action': col.key === '__action__',
              }"
              :style="col.width ? { width: col.width } : undefined"
              @click="col.sortable ? sortBy(col.key) : undefined"
            >
              {{ col.label }}
              <span v-if="col.sortable" class="issue-table__sort-mark">{{ sortMark(col.key) }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="issue in filteredIssues"
            :key="`row-${issue.id}`"
            class="table-row-clickable issue-table__row"
            @click="$emit('row-click', issue)"
          >
            <td
              v-for="col in columns"
              :key="`cell-${col.key}-${issue.id}`"
              :class="col.cellClass"
              :title="cellTitle(col, issue)"
            >
              <template v-if="col.key === '__severity__'">
                <span class="issue-badge" :class="severityToneClass(getValue(issue, filter.severityField))">
                  {{ severityLabel(getValue(issue, filter.severityField)) }}
                </span>
              </template>
              <template v-else-if="col.key === '__action__'">
                <span class="issue-table__action">查看 →</span>
              </template>
              <template v-else>
                {{ col.render ? col.render(issue) : (getValue(issue, col.key) || '-') }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="muted issue-table-empty" v-else-if="issues.length">
      没有符合筛选条件的漏洞，可调整严重度或重置筛选。
    </div>
    <div class="muted issue-table-empty" v-else>{{ emptyMessage || '当前没有可展示的漏洞明细。' }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { severityLabel } from "../../utils/report-labels";

export type IssueTableColumn = {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  render?: (issue: any) => string;
  cellClass?: string;
};

export type IssueTableFilter = {
  severityField: string;
  categoryField: string;
  searchFields?: string[];
  categoryLabel?: string;
  searchPlaceholder?: string;
};

const props = defineProps<{
  issues: any[];
  columns: IssueTableColumn[];
  filter: IssueTableFilter;
  emptyMessage?: string;
}>();

defineEmits<{ (e: "row-click", issue: any): void }>();

const SEVERITY_OPTIONS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;
const SEVERITY_ORDER: Record<string, number> = {
  CRITICAL: 4,
  HIGH: 3,
  MEDIUM: 2,
  LOW: 1,
  INFO: 0,
  UNKNOWN: 0,
};

const filterSeverities = ref<string[]>([]);
const filterCategory = ref("");
const filterKeyword = ref("");
const sortKey = ref<string>("__severity__");
const sortDir = ref<"asc" | "desc">("desc");

function getValue(obj: any, key: string): string {
  if (!obj || !key) return "";
  return String(obj[key] ?? "");
}

function severityToneClass(label?: string) {
  if (!label) return "";
  const value = label.toUpperCase();
  if (value.includes("CRITICAL") || value.includes("HIGH")) return "is-danger";
  if (value.includes("MEDIUM")) return "is-warning";
  if (value.includes("LOW")) return "is-info";
  return "";
}

function cellTitle(col: IssueTableColumn, issue: any): string | undefined {
  if (col.key === "__severity__" || col.key === "__action__") return undefined;
  const value = col.render ? col.render(issue) : getValue(issue, col.key);
  return value && value.length > 24 ? value : undefined;
}

const categoryOptions = computed<string[]>(() => {
  const set = new Set<string>();
  props.issues.forEach((i) => {
    const v = getValue(i, props.filter.categoryField);
    if (v) set.add(v);
  });
  return Array.from(set).sort();
});

const filteredIssues = computed(() => {
  let list = props.issues.slice();
  const sevField = props.filter.severityField;
  if (filterSeverities.value.length) {
    list = list.filter((i) => {
      const lvl = getValue(i, sevField).toUpperCase() || "UNKNOWN";
      return filterSeverities.value.includes(lvl);
    });
  }
  if (filterCategory.value) {
    const catField = props.filter.categoryField;
    list = list.filter((i) => getValue(i, catField) === filterCategory.value);
  }
  if (filterKeyword.value.trim() && props.filter.searchFields && props.filter.searchFields.length) {
    const kw = filterKeyword.value.trim().toLowerCase();
    list = list.filter((i) =>
      props.filter.searchFields!.some((f) => getValue(i, f).toLowerCase().includes(kw))
    );
  }
  list.sort((a, b) => {
    let cmp = 0;
    if (sortKey.value === "__severity__") {
      const la = getValue(a, sevField).toUpperCase() || "UNKNOWN";
      const lb = getValue(b, sevField).toUpperCase() || "UNKNOWN";
      cmp = (SEVERITY_ORDER[la] ?? 0) - (SEVERITY_ORDER[lb] ?? 0);
    } else {
      cmp = getValue(a, sortKey.value).localeCompare(getValue(b, sortKey.value));
    }
    return sortDir.value === "desc" ? -cmp : cmp;
  });
  return list;
});

function toggleSeverityFilter(level: string) {
  const idx = filterSeverities.value.indexOf(level);
  if (idx >= 0) filterSeverities.value.splice(idx, 1);
  else filterSeverities.value.push(level);
}

function resetFilters() {
  filterSeverities.value = [];
  filterCategory.value = "";
  filterKeyword.value = "";
}

function sortBy(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === "desc" ? "asc" : "desc";
  } else {
    sortKey.value = key;
    sortDir.value = "desc";
  }
}

function sortMark(key: string) {
  if (sortKey.value !== key) return "⇅";
  return sortDir.value === "desc" ? "↓" : "↑";
}
</script>

<style scoped>
.issue-table-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.issue-table-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(18, 50, 77, 0.04);
}

.issue-table-filter-bar__group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.issue-table-filter-bar__label {
  font-size: 12px;
  font-weight: 700;
  margin-right: 4px;
}

.issue-table-filter-bar__select {
  min-width: 160px;
  flex: 0 1 200px;
}

.issue-table-filter-bar__search {
  flex: 1 1 200px;
  min-width: 200px;
}

.issue-table-filter-bar__summary {
  flex-basis: 100%;
  font-size: 12px;
  margin-top: 2px;
}

.severity-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--line-strong, rgba(56, 104, 153, 0.28));
  background: #fff;
  color: var(--ink-700, #49627d);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.16s ease;
}

.severity-chip:hover {
  border-color: var(--accent-500, #17a2ad);
  color: var(--ink-900, #132238);
}

.severity-chip--critical {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.35);
}
.severity-chip--high {
  color: #b42318;
  border-color: rgba(239, 68, 68, 0.45);
}
.severity-chip--medium {
  color: #b45309;
  border-color: rgba(217, 119, 6, 0.35);
}
.severity-chip--low {
  color: #1d4ed8;
  border-color: rgba(37, 99, 235, 0.35);
}

.severity-chip--critical.severity-chip--active,
.severity-chip--high.severity-chip--active {
  background: #b42318;
  border-color: #b42318;
  color: #fff;
}
.severity-chip--medium.severity-chip--active {
  background: #d97706;
  border-color: #d97706;
  color: #fff;
}
.severity-chip--low.severity-chip--active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.issue-table-wrap {
  overflow-x: auto;
  border-radius: 16px;
}

.issue-table th,
.issue-table td {
  vertical-align: middle;
}

.issue-table__th-sort {
  cursor: pointer;
  user-select: none;
  transition: color 0.16s ease;
}

.issue-table__th-sort:hover {
  color: var(--accent-500, #17a2ad);
}

.issue-table__sort-mark {
  display: inline-block;
  margin-left: 4px;
  color: var(--ink-700, #49627d);
  font-weight: 600;
}

.issue-table__th-action {
  width: 80px;
}

.issue-table__action {
  color: var(--accent-500, #17a2ad);
  font-weight: 800;
  font-size: 12px;
  white-space: nowrap;
}

.issue-table__row:hover .issue-table__action {
  color: #0d7b83;
}

.issue-table-empty {
  padding: 24px 12px;
  text-align: center;
}
</style>
