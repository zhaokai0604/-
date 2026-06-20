import { createRouter, createWebHistory } from 'vue-router'

import WorkspaceLayout from './layouts/WorkspaceLayout.vue'
import DashboardView from './views/DashboardView.vue'
import AnalyzeView from './views/AnalyzeView.vue'
import BatchView from './views/BatchView.vue'
import ResumesView from './views/ResumesView.vue'
import ResumeDetailView from './views/ResumeDetailView.vue'
import JobsView from './views/JobsView.vue'
import TasksView from './views/TasksView.vue'
import ReportsView from './views/ReportsView.vue'
import AdminUsersView from './views/admin/AdminUsersView.vue'
import AdminJobsView from './views/admin/AdminJobsView.vue'
import AdminSystemView from './views/admin/AdminSystemView.vue'
import TeacherDashboardView from './views/teacher/TeacherDashboardView.vue'

const EmptyView = { template: '<div />' }

const workspaceChildren = [
  { path: '', redirect: '/dashboard' },
  { path: 'dashboard', name: 'dashboard', component: DashboardView },
  { path: 'workspace/analyze', name: 'workspace-analyze', component: AnalyzeView },
  { path: 'workspace/batch', name: 'workspace-batch', component: BatchView },
  { path: 'workspace/resumes', name: 'workspace-resumes', component: ResumesView },
  { path: 'workspace/resumes/:recordId', name: 'workspace-resume-detail', component: ResumeDetailView },
  { path: 'workspace/jobs', name: 'workspace-jobs', component: JobsView },
  { path: 'workspace/tasks', name: 'workspace-tasks', component: TasksView },
  { path: 'workspace/reports', name: 'workspace-reports', component: ReportsView },
  { path: 'admin/users', name: 'admin-users', component: AdminUsersView },
  { path: 'admin/jobs', name: 'admin-jobs', component: AdminJobsView },
  { path: 'admin/system', name: 'admin-system', component: AdminSystemView },
  { path: 'teacher/dashboard', name: 'teacher-dashboard', component: TeacherDashboardView },
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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
