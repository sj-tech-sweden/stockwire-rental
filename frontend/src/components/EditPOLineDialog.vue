<template>
  <q-dialog :model-value="modelValue" persistent style="width: 500px; max-width: 95vw" @update:model-value="(v) => emit('update:modelValue', v)">
    <q-card style="width: 500px; max-width: 95vw">
      <q-card-section class="row items-center">
        <div class="text-h6 q-mr-auto">{{ t('purchasing.editLine') }}</div>
        <q-btn flat round icon="close" @click="close" />
      </q-card-section>

      <q-card-section class="q-gutter-md">
        <div class="row q-col-gutter-sm">
          <div class="col-8">
            <q-input v-model="form.name" :label="t('purchasing.name')" dense outlined />
          </div>
          <div class="col-4">
            <q-input v-model="form.sku" :label="t('purchasing.sku')" dense outlined />
          </div>
        </div>
        <div class="row q-col-gutter-sm">
          <div class="col-4">
            <q-input v-model.number="form.qty" type="number" min="1" :label="t('purchasing.qty')" dense outlined />
          </div>
          <div class="col-4">
            <q-input v-model.number="form.unit_cost" type="number" step="0.01" :label="t('purchasing.unitCost')" dense outlined />
          </div>
          <div class="col-4">
            <q-select
              v-model="form.currency"
              :options="currencyOptions"
              :label="t('purchasing.currency')"
              dense
              outlined
              emit-value
              map-options
            />
          </div>
        </div>
        <div v-if="line && line.received_qty" class="text-caption text-negative">
          {{ t('purchasing.lineReceivedLocked') }}
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat color="negative" icon="delete" :label="t('purchasing.deleteLine')" @click="remove" />
        <q-btn flat :label="t('app.actions.cancel')" @click="close" />
        <q-btn color="primary" :label="t('app.actions.save')" :loading="saving" :disable="!!(line && line.received_qty)" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { api } from '../boot/axios'

const { t } = useI18n()
const $q = useQuasar()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  poId: { type: Number, required: true },
  line: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved', 'deleted'])

const form = ref({ name: '', sku: '', qty: 1, unit_cost: null, currency: null })
const saving = ref(false)
const currencyOptions = [
  'SEK', 'EUR', 'USD', 'GBP', 'NOK', 'DKK', 'CHF', 'PLN', 'CZK', 'HUF',
].map((c) => ({ label: c, value: c }))

watch(
  () => props.line,
  (line) => {
    if (line) {
      form.value = {
        name: line.name || '',
        sku: line.sku || '',
        qty: line.qty,
        unit_cost: line.unit_cost,
        currency: line.currency,
      }
    }
  },
  { immediate: true },
)

function close() {
  emit('update:modelValue', false)
}

async function save() {
  saving.value = true
  try {
    await api.put(
      `/api/v1/purchasing/purchase-orders/${props.poId}/lines/${props.line.id}`,
      {
        name: form.value.name,
        sku: form.value.sku,
        qty: form.value.qty,
        unit_cost: form.value.unit_cost,
        currency: form.value.currency,
      },
    )
    $q.notify({ type: 'positive', message: t('purchasing.lineSaved') })
    emit('saved')
    close()
  } catch {
    $q.notify({ type: 'negative', message: t('purchasing.lineUpdateFailed') })
  } finally {
    saving.value = false
  }
}

async function remove() {
  try {
    await api.delete(
      `/api/v1/purchasing/purchase-orders/${props.poId}/lines/${props.line.id}`,
    )
    $q.notify({ type: 'positive', message: t('purchasing.lineDeleted') })
    emit('deleted')
    close()
  } catch {
    $q.notify({ type: 'negative', message: t('purchasing.lineUpdateFailed') })
  }
}
</script>
