import { RouterLink, useRoute } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const navItems = [
  { path: '/dashboard', icon: 'pi-chart-bar', label: 'Dashboard' },
  { path: '/sensors', icon: 'pi-wifi', label: 'Sensors' },
  { path: '/reports', icon: 'pi-file', label: 'Reports' },
  { path: '/config', icon: 'pi-cog', label: 'Configuration' },
]

  auth.logout()
  // Force reload to clear any state and go to login
  window.location.href = '/login'
}

// Password Change Logic
const showPasswordModal = ref(false)
const isChangingPass = ref(false)
const passForm = ref({ current: '', new: '' })

async function handlePasswordChange() {
  isChangingPass.value = true
  try {
    await auth.changePassword(passForm.value.current, passForm.value.new)
    alert('Password changed successfully')
    showPasswordModal.value = false
    passForm.value = { current: '', new: '' }
  } catch (e: any) {
    alert('Failed: ' + (e.response?.data?.detail || e.message))
  } finally {
    isChangingPass.value = false
  }
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
        <div class="user-profile" style="margin-bottom: 1rem; padding: 0 1rem;">
          <small style="color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Logged in as</small>
          <div style="font-weight: 500; display: flex; align-items: center; gap: 0.5rem;">
            <i class="pi pi-user" style="background: var(--surface-hover); padding: 0.4rem; border-radius: 50%;"></i>
            <span>{{ auth.user?.username }}</span>
          </div>
        </div>
        
        <button class="nav-item action-btn" @click="showPasswordModal = true">
          <i class="pi pi-key"></i>
          <span>Change Password</span>
        </button>
        
        <button class="nav-item action-btn error-hover" @click="handleLogout">
          <i class="pi pi-sign-out"></i>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>

    <!-- Change Password Modal -->
    <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
      <div class="modal-content" style="max-width: 400px;">
        <div class="modal-header">
          <h2>Change Password</h2>
          <button class="btn-close" @click="showPasswordModal = false"><i class="pi pi-times"></i></button>
        </div>
        <form @submit.prevent="handlePasswordChange" class="modal-body">
          <div class="form-group">
            <label class="form-label">Current Password</label>
            <input v-model="passForm.current" type="password" class="form-input" required />
          </div>
          <div class="form-group">
             <label class="form-label">New Password</label>
             <input v-model="passForm.new" type="password" class="form-input" required minlength="8" />
             <small class="text-muted">Min 8 characters</small>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showPasswordModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="isChangingPass">
              <i v-if="isChangingPass" class="pi pi-spin pi-spinner"></i>
              {{ isChangingPass ? 'Updating...' : 'Update Password' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <main class="main-content">
      <slot />
    </main>
  </div>
</template>
