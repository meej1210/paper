import { createRouter, createWebHistory } from "vue-router";

import AdminDashboardView from "../views/AdminDashboardView.vue";
import AuditLogView from "../views/AuditLogView.vue";
import LoginView from "../views/LoginView.vue";
import RegisterView from "../views/RegisterView.vue";
import ScanCreateView from "../views/ScanCreateView.vue";
import TaskDetailView from "../views/TaskDetailView.vue";
import TaskListView from "../views/TaskListView.vue";
import { isAuthenticated } from "../store/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/tasks"
    },
    {
      path: "/login",
      component: LoginView,
      meta: {
        public: true,
        title: "登录",
        description: "登录后即可进入安全工作台，统一发起和跟进扫描任务。"
      }
    },
    {
      path: "/register",
      component: RegisterView,
      meta: {
        public: true,
        title: "注册",
        description: "创建平台账号，开始体验静态审计与动态扫描流程。"
      }
    },
    {
      path: "/scan/new",
      name: "scan-create",
      component: ScanCreateView,
      meta: {
        title: "新建扫描",
        description: "统一填写扫描配置，按场景切换 SAST 和 DAST。"
      }
    },
    {
      path: "/sast",
      redirect: () => ({ path: "/scan/new", query: { type: "sast" } })
    },
    {
      path: "/dast",
      redirect: () => ({ path: "/scan/new", query: { type: "dast" } })
    },
    {
      path: "/tasks",
      name: "task-list",
      component: TaskListView,
      meta: {
        title: "工作台",
        description: "在一个入口查看任务概览、筛选队列并进入报告详情。"
      }
    },
    {
      path: "/tasks/:id",
      name: "task-detail",
      component: TaskDetailView,
      props: true,
      meta: {
        title: "任务详情",
        description: "先看执行状态和结论，再继续下钻报告与整改信息。"
      }
    },
    {
      path: "/admin",
      component: AdminDashboardView,
      meta: {
        title: "管理看板",
        description: "管理员专属的全局任务、风险、审计和运行状态总览。"
      }
    },
    {
      path: "/audit-logs",
      component: AuditLogView,
      meta: {
        title: "审计日志",
        description: "跟踪用户操作和关键系统行为，方便回溯与审计。"
      }
    }
  ]
});

router.beforeEach((to) => {
  if (!to.meta.public && !isAuthenticated()) {
    return "/login";
  }
  return true;
});

router.afterEach((to) => {
  const title = typeof to.meta.title === "string" ? to.meta.title : "安全审计工作台";
  document.title = `${title} - 安全审计平台`;
});

export default router;
