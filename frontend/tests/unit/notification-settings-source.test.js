import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('notification settings source wiring', () => {
  const frontendRoot = resolve(import.meta.dirname, '../..')

  it('exposes customer and job email notification toggles in source', () => {
    const customerPage = readFileSync(resolve(frontendRoot, 'src/pages/CustomerDetailPage.vue'), 'utf8')
    const jobPage = readFileSync(resolve(frontendRoot, 'src/pages/JobDetailPage.vue'), 'utf8')

    expect(customerPage).toContain("email_notifications_enabled")
    expect(customerPage).toContain("customers.emailNotificationsEnabled")
    expect(jobPage).toContain("email_notifications_enabled")
    expect(jobPage).toContain("jobs.emailNotificationsEnabled")
  })

  it('wires profile notification channel and web notification subscription source', () => {
    const profilePage = readFileSync(resolve(frontendRoot, 'src/pages/ProfilePage.vue'), 'utf8')
    const authStore = readFileSync(resolve(frontendRoot, 'src/stores/auth.js'), 'utf8')

    expect(profilePage).toContain("notification_channel")
    expect(profilePage).toContain("/api/v1/notifications/subscriptions")
    expect(profilePage).toContain("Notification.requestPermission")
    expect(authStore).toContain("notification_channel")
  })
})
