import { createRouter, createWebHistory } from 'vue-router'

import WorkspaceLayout from './layouts/WorkspaceLayout.vue'

const EmptyView = { template: '<div />' }
const NotFoundView = {
  template: `
    <section class="empty-state">
      <strong>页面不存在</strong>
      <p>请从左侧导航返回工作台。</p>
    </section>
  `,
}

const workspaceChildren = [
  { path: '', redirect: '/dashboard' },
  { path: 'dashboard', name: 'dashboard', component: () => import('./views/DashboardView.vue') },
  { path: 'workspace/analyze', name: 'workspace-analyze', component: () => import('./views/AnalyzeView.vue') },
  { path: 'workspace/batch', name: 'workspace-batch', component: () => import('./views/BatchView.vue') },
  { path: 'workspace/interview', name: 'workspace-interview', component: () => import('./views/InterviewView.vue') },
  { path: 'workspace/resumes', name: 'workspace-resumes', component: () => import('./views/ResumesView.vue') },
  {
    path: 'workspace/resumes/:recordId',
    name: 'workspace-resume-detail',
    component: () => import('./views/ResumeDetailView.vue'),
  },
  { path: 'workspace/jobs', name: 'workspace-jobs', component: () => import('./views/JobsView.vue') },
  { path: 'workspace/tasks', name: 'workspace-tasks', component: () => import('./views/TasksView.vue') },
  { path: 'workspace/reports', name: 'workspace-reports', component: () => import('./views/ReportsView.vue') },
  { path: 'admin/users', name: 'admin-users', component: () => import('./views/admin/AdminUsersView.vue'), meta: { role: 'admin' } },
  { path: 'admin/jobs', name: 'admin-jobs', component: () => import('./views/admin/AdminJobsView.vue'), meta: { role: 'admin' } },
  { path: 'admin/system', name: 'admin-system', component: () => import('./views/admin/AdminSystemView.vue'), meta: { role: 'admin' } },
  {
    path: 'teacher/dashboard',
    name: 'teacher-dashboard',
    component: () => import('./views/teacher/TeacherDashboardView.vue'),
    meta: { role: 'teacher' },
  },
  {
    path: 'teacher/classes',
    name: 'teacher-classes',
    component: () => import('./views/teacher/TeacherClassView.vue'),
    meta: { role: 'teacher' },
  },
  {
    path: 'teacher/records',
    name: 'teacher-records',
    component: () => import('./views/teacher/TeacherRecordsView.vue'),
    meta: { role: 'teacher' },
  },
]

const routes = [
  {
    path: '/',
    component: WorkspaceLayout,
    children: workspaceChildren,
  },
  {
    path: '/login',
    component: WorkspaceLayout,
    children: [{ path: '', name: 'login', component: EmptyView }],
  },
  {
    path: '/register',
    component: WorkspaceLayout,
    children: [{ path: '', name: 'register', component: EmptyView }],
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export function installRouteGuards(getPlatform) {
  router.beforeEach((to) => {
    const platform = getPlatform()
    const requiredRole = to.meta?.role
    if (requiredRole === 'admin' && !platform.isAdmin) {
      return { name: 'dashboard' }
    }
    if (requiredRole === 'teacher' && !platform.isTeacherOrAdmin) {
      return { name: 'dashboard' }
    }
    return true
  })
}

export default router
