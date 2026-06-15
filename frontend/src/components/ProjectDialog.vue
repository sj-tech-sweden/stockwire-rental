<template>
  <q-dialog v-model="dialogOpen" persistent :maximized="isPhone">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 520px; max-width: 95vw'" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ project ? t('projects.editProject') : t('projects.newProject') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="saveProject">
          <q-input
            v-model="form.name"
            :label="t('projects.name')"
            outlined
            dense
            :rules="[v => !!v || t('login.required')]"
          />

          <q-input
            v-model="form.description"
            :label="t('projects.description')"
            type="textarea"
            autogrow
            outlined
            dense
            class="q-mt-sm"
          />

          <q-select
            v-model="form.customer_id"
            :options="customerOptions"
            :label="t('projects.customer')"
            outlined
            dense
            clearable
            use-input
            fill-input
            input-debounce="0"
            emit-value
            map-options
            class="q-mt-sm"
            @filter="filterCustomerOptions"
          />

          <CustomerCreateInline class="q-mt-sm" @created="onCustomerCreated" />

          <q-select
            v-model="form.venue_id"
            :options="venueOptions"
            :label="t('projects.venue')"
            outlined
            dense
            clearable
            use-input
            fill-input
            input-debounce="0"
            emit-value
            map-options
            class="q-mt-sm"
            @filter="filterVenueOptions"
          />

          <VenueCreateInline class="q-mt-sm" @created="onVenueCreated" />

          <div class="row q-col-gutter-sm q-mt-sm">
            <div class="col-12 col-md-6">
              <q-input v-model="form.start_date" :label="t('projects.startDate')" type="date" outlined dense />
            </div>
            <div class="col-12 col-md-6">
              <q-input v-model="form.end_date" :label="t('projects.endDate')" type="date" outlined dense />
            </div>
          </div>

          <q-input
            v-model="form.notes"
            :label="t('projects.notes')"
            type="textarea"
            autogrow
            outlined
            dense
            class="q-mt-sm"
          />

          <q-select
            v-model="form.status"
            :options="statusOptions"
            :label="t('projects.status')"
            outlined
            dense
            emit-value
            map-options
            class="q-mt-sm"
          />

          <div class="row justify-end q-mt-md q-gutter-sm">
            <q-btn flat :label="t('app.actions.cancel')" v-close-popup />
            <q-btn color="primary" type="submit" :label="t('projects.create')" :loading="saving" unelevated />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useCustomersStore } from '../stores/customers'
import { useVenuesStore } from '../stores/venues'
import { useProjectsStore } from '../stores/projects'
import CustomerCreateInline from './CustomerCreateInline.vue'
import VenueCreateInline from './VenueCreateInline.vue'

const props = defineProps({
  modelValue: Boolean,
  project: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const customersStore = useCustomersStore()
const venuesStore = useVenuesStore()
const projectsStore = useProjectsStore()

const isPhone = computed(() => $q.screen.width < 600)
const dialogOpen = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })

const formRef = ref(null)
const saving = ref(false)

const form = ref(emptyForm())

function emptyForm() {
  return {
    name: '',
    description: null,
    customer_id: null,
    venue_id: null,
    start_date: null,
    end_date: null,
    notes: null,
    status: 'active',
  }
}

const statusOptions = [
  { label: t('projects.statusActive'), value: 'active' },
  { label: t('projects.statusCompleted'), value: 'completed' },
  { label: t('projects.statusCancelled'), value: 'cancelled' },
]

const customerOptions = computed(() => {
  return customersStore.customers.map(c => ({ label: c.name, value: c.id }))
})

const venueOptions = computed(() => {
  return venuesStore.venues.map(v => ({ label: v.name, value: v.id }))
})

let customerFilterTimer = null
let venueFilterTimer = null

function filterCustomerOptions(input, update) {
  clearTimeout(customerFilterTimer)
  customerFilterTimer = setTimeout(() => {
    update()
  }, 150)
}

function filterVenueOptions(input, update) {
  clearTimeout(venueFilterTimer)
  venueFilterTimer = setTimeout(() => {
    update()
  }, 150)
}

function onCustomerCreated(customer) {
  form.value.customer_id = customer.id
}

function onVenueCreated(venue) {
  form.value.venue_id = venue.id
}

watch(() => props.modelValue, (open) => {
  if (open) {
    if (props.project) {
      form.value = {
        name: props.project.name || '',
        description: props.project.description || null,
        customer_id: props.project.customer_id || null,
        venue_id: props.project.venue_id || null,
        start_date: props.project.start_date || null,
        end_date: props.project.end_date || null,
        notes: props.project.notes || null,
        status: props.project.status || 'active',
      }
    } else {
      form.value = emptyForm()
    }
    if (!customersStore.customers.length) {
      customersStore.fetchAll()
    }
    if (!venuesStore.venues.length) {
      venuesStore.fetchAll()
    }
  }
})

async function saveProject() {
  const valid = await formRef.value.validate()
  if (!valid) return
  saving.value = true
  try {
    const payload = { ...form.value }
    if (props.project) {
      await projectsStore.updateProject(props.project.id, payload)
    } else {
      await projectsStore.createProject(payload)
    }
    emit('saved')
    dialogOpen.value = false
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.errorOccurred') })
  } finally {
    saving.value = false
  }
}
</script>
