<template>
  <q-card class="ec-card q-pa-md q-mt-md">
    <div class="row items-center justify-between q-mb-sm">
      <div class="ec-card-title">{{ t('settings.integrations.stagewire.title') }}</div>
      <q-btn
        color="secondary"
        icon="add"
        :label="t('settings.integrations.stagewire.addInstance')"
        dense
        unelevated
        @click="addInstance"
      />
    </div>
    <div class="text-caption ec-text-muted q-mb-sm">
      {{ t('settings.integrations.stagewire.description') }}
    </div>

    <div
      v-for="(inst, index) in instances"
      :key="inst._key"
      class="ec-card ec-card--inset q-pa-md q-mb-md"
    >
      <div class="row q-col-gutter-sm">
        <div class="col-12 col-md-3">
          <q-input
            v-model="inst.id"
            :label="t('settings.integrations.stagewire.instanceId')"
            outlined
            dense
          />
        </div>
        <div class="col-12 col-md-3">
          <q-input
            v-model="inst.name"
            :label="t('settings.integrations.stagewire.instanceName')"
            outlined
            dense
          />
        </div>
        <div class="col-12 col-md-4">
          <q-input
            v-model="inst.api_url"
            :label="t('settings.integrations.stagewire.apiUrl')"
            :hint="t('settings.integrations.stagewire.apiUrlHint')"
            outlined
            dense
          />
        </div>
        <div class="col-12 col-md-2 row items-center justify-end">
          <q-toggle
            v-model="inst.enabled"
            :label="t('settings.integrations.stagewire.enabled')"
            color="primary"
          />
        </div>
        <div class="col-12 col-md-6">
          <q-input
            v-model="inst.api_key"
            type="password"
            :label="t('settings.integrations.stagewire.apiKey')"
            :placeholder="inst.has_api_key && !inst.api_key ? t('settings.integrations.stagewire.apiKeySaved') : ''"
            :hint="t('settings.integrations.stagewire.apiKeyHint')"
            outlined
            dense
          />
        </div>
      </div>

      <div class="row items-center q-gutter-sm q-mt-sm">
        <q-btn
          color="secondary"
          icon="wifi_tethering"
          :label="t('settings.integrations.stagewire.test')"
          unelevated
          dense
          :loading="testing[inst.id]"
          :disable="!inst.id"
          @click="testInstance(inst)"
        />
        <q-badge
          :color="statusFor(inst).color"
          :label="statusFor(inst).label"
        />
        <span
          v-if="results[inst.id]"
          class="text-caption ec-text-muted"
        >
          {{ results[inst.id].message }}
        </span>
        <q-space />
        <q-btn
          flat
          dense
          color="negative"
          icon="delete"
          :label="t('settings.integrations.stagewire.remove')"
          @click="removeInstance(index)"
        />
      </div>
    </div>

    <div
      v-if="loadError"
      class="row items-center q-gutter-sm q-mb-sm"
    >
      <span class="text-negative text-caption">{{ loadError }}</span>
      <q-btn
        flat
        dense
        icon="refresh"
        :label="t('settings.integrations.stagewire.reload')"
        @click="load"
      />
    </div>
    <div
      v-else-if="loaded && !instances.length"
      class="text-caption ec-text-muted q-mb-sm"
    >
      {{ t('settings.integrations.stagewire.noInstances') }}
    </div>

    <div class="row justify-end q-mt-sm">
      <q-btn
        color="positive"
        unelevated
        :label="t('settings.integrations.stagewire.save')"
        :loading="saving"
        @click="save"
      />
    </div>
    <div
      v-if="message"
      class="text-caption q-mt-xs"
      :class="messageError ? 'text-negative' : 'text-positive'"
    >
      {{ message }}
    </div>
  </q-card>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../boot/axios';

const { t } = useI18n({ useScope: 'global' });

const instances = ref([]);
const results = ref({});
const testing = ref({});
const saving = ref(false);
const message = ref('');
const messageError = ref(false);
let keySeq = 0;

function toDraft(item) {
  keySeq += 1;
  return {
    _key: `sw-${keySeq}`,
    id: item.id || 'stagewire-main',
    name: item.name || item.id || 'Stagewire',
    enabled: !!item.enabled,
    api_url: item.api_url || '',
    api_key: '',
    has_api_key: !!item.has_api_key,
    default_customer_id: item.default_customer_id ?? null,
  };
}

const loaded = ref(false);
const loadError = ref('');

async function load() {
  loadError.value = '';
  try {
    const { data } = await api.get('/api/v1/settings/integrations/stagewire-instances');
    instances.value = (data || []).map(toDraft);
    loaded.value = true;
    // Only a successful, empty response means "not configured".
    if (!instances.value.length) addInstance();
    for (const inst of instances.value) {
      if (inst.enabled && inst.api_url) testInstance(inst);
    }
  } catch (err) {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail;
    loadError.value = status
      ? `${t('settings.integrations.stagewire.loadFailed')} (HTTP ${status}${detail ? `: ${detail}` : ''})`
      : t('settings.integrations.stagewire.loadFailed');
  }
}

function addInstance() {
  const n = instances.value.length + 1;
  instances.value.push(
    toDraft({ id: n === 1 ? 'stagewire-main' : `stagewire-${n}`, name: 'Stagewire', enabled: true }),
  );
}

function removeInstance(index) {
  instances.value.splice(index, 1);
}

async function save() {
  saving.value = true;
  message.value = '';
  messageError.value = false;
  try {
    const payload = {
      instances: instances.value.map((inst) => ({
        id: inst.id,
        name: inst.name,
        enabled: inst.enabled,
        api_url: inst.api_url || null,
        api_key: inst.api_key || null,
        default_customer_id: inst.default_customer_id,
      })),
    };
    const { data } = await api.put('/api/v1/settings/integrations/stagewire-instances', payload);
    instances.value = (data || []).map(toDraft);
    message.value = t('settings.integrations.stagewire.saved');
  } catch (err) {
    messageError.value = true;
    message.value = err?.response?.data?.detail || t('settings.integrations.stagewire.saveFailed');
  } finally {
    saving.value = false;
  }
}

async function testInstance(inst) {
  testing.value = { ...testing.value, [inst.id]: true };
  try {
    const { data } = await api.post(
      `/api/v1/settings/integrations/stagewire-instances/${encodeURIComponent(inst.id)}/test`,
      { api_url: inst.api_url || null, api_key: inst.api_key || null },
    );
    results.value = {
      ...results.value,
      [inst.id]: { ok: !!data.ok, message: data.message || '' },
    };
  } catch (err) {
    results.value = {
      ...results.value,
      [inst.id]: {
        ok: false,
        message: err?.response?.data?.detail || t('settings.integrations.stagewire.notConnected'),
      },
    };
  } finally {
    testing.value = { ...testing.value, [inst.id]: false };
  }
}

function statusFor(inst) {
  const r = results.value[inst.id];
  if (!r) return { color: 'grey-7', label: t('settings.integrations.stagewire.notTested') };
  return r.ok
    ? { color: 'positive', label: t('settings.integrations.stagewire.connected') }
    : { color: 'negative', label: t('settings.integrations.stagewire.notConnected') };
}

onMounted(() => {
  load().catch(() => {});
});
</script>
