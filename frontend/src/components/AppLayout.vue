<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const navItems = [
  { path: '/dashboard', icon: 'pi-chart-bar', label: 'Dashboard' },
  { path: '/sensors', icon: 'pi-wifi', label: 'Sensors' },
  { path: '/reports', icon: 'pi-file', label: 'Reports' },
  { path: '/config', icon: 'pi-cog', label: 'Configuration' },
]

function handleLogout() {
  auth.logout()
  window.location.href = '/login'
}
</script>

<template>
  <div class="app-container">
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="sidebar-logo">
          <i class="pi pi-bolt"></i>
        </div>
        <span class="sidebar-title">DaTaK</span>
      </div>

      <nav>
        <ul class="nav-menu">
          <li v-for="item in navItems" :key="item.path">
            <RouterLink 
              :to="item.path" 
              class="nav-item"
              :class="{ active: route.path === item.path }"
            >
              <i :class="['pi', item.icon]"></i>
              <span>{{ item.label }}</span>
            </RouterLink>
          </li>
        </ul>
      </nav>

      <div style="margin-top: auto; padding-top: 1rem; border-top: 1px solid var(--border);">
        <div class="nav-item" style="margin-bottom: 0.5rem;">
          <i class="pi pi-user"></i>
          <span>{{ auth.user?.username }}</span>
        </div>
        <button class="nav-item" :class="{ active: route.path === '/reports' }" @click="router.push('/reports')">
        <i class="pi pi-file"></i>
        <span>Reports</span>
      </button>
      <button class="nav-item" :class="{ active: route.path === '/report-jobs' }" @click="router.push('/report-jobs')">
        <i class="pi pi-cog"></i>
        <span>Jobs</span>
      </button>
      </div>
    </aside>

    <main class="main-content">
      <slot />
    </main>
  </div>
</template>
