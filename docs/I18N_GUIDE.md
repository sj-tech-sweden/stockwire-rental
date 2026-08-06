# Internationalization (i18n) Guide

> Last reviewed: 2026-08-06

## Overview

Stockwire Rental supports multiple languages through Vue I18n. Currently supported: English (en) and Swedish (sv).

**Location:** `frontend/src/i18n/`

---

## Structure

```
frontend/src/i18n/
├── index.js                 # i18n setup and locale resolution
├── prefillContent.js        # Template/prefill content
└── locales/
    ├── en.js                # English translations (2443 lines)
    └── sv.js                # Swedish translations
```

---

## Locale Resolution

The app determines locale in this order:

1. **User Preference** - Stored in user profile
2. **Browser Locale** - From `navigator.language`
3. **Company Default** - From company settings
4. **Fallback** - English

---

## Translation Structure

### File Format

```javascript
// i18n/locales/en.js
export default {
  app: {
    name: 'Stockwire Rental',
    nav: {
      inventory: 'Inventory',
      jobs: 'Jobs',
      // ...
    }
  },
  inventory: {
    products: {
      title: 'Products',
      // ...
    }
  }
}
```

### Key Organization

Translations are organized by domain:

```
app.*                    - App-wide strings
app.nav.*                - Navigation items
app.actions.*            - Button labels
inventory.*              - Inventory module
inventory.products.*     - Products section
inventory.devices.*      - Devices section
jobs.*                   - Jobs module
customers.*              - Customers module
crew.*                   - Crew module
finance.*                - Finance module
settings.*               - Settings module
```

---

## Adding Translations

### Step 1: Add to English

```javascript
// i18n/locales/en.js
export default {
  myModule: {
    title: 'My Module',
    actions: {
      create: 'Create Item',
      edit: 'Edit Item',
      delete: 'Delete Item'
    },
    fields: {
      name: 'Name',
      description: 'Description'
    }
  }
}
```

### Step 2: Add to Swedish

```javascript
// i18n/locales/sv.js
export default {
  myModule: {
    title: 'Min modul',
    actions: {
      create: 'Skapa objekt',
      edit: 'Redigera objekt',
      delete: 'Ta bort objekt'
    },
    fields: {
      name: 'Namn',
      description: 'Beskrivning'
    }
  }
}
```

### Step 3: Use in Component

```vue
<template>
  <div>
    <h1>{{ $t('myModule.title') }}</h1>
    <q-btn :label="$t('myModule.actions.create')" />
  </div>
</template>
```

---

## Usage Patterns

### In Templates

```vue
<!-- Simple translation -->
<p>{{ $t('app.actions.save') }}</p>

<!-- With interpolation -->
<p>{{ $t('inventory.products.count', { count: 5 }) }}</p>

<!-- Pluralization -->
<p>{{ $t('inventory.products.item', count) }}</p>
```

### In Script

```vue
<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const label = t('app.actions.save')
</script>
```

### Dynamic Keys

```vue
<template>
  <div>{{ $t(`inventory.${entity}.title`) }}</div>
</template>
```

---

## Prefill Content

Template content for predefined data:

```javascript
// i18n/prefillContent.js
export default {
  categories: {
    audio: {
      name: 'Audio',
      subcategories: ['Speakers', 'Microphones', 'Mixers']
    }
  }
}
```

---

## Common Patterns

### Button Labels

```javascript
app: {
  actions: {
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    create: 'Create',
    close: 'Close',
    reset: 'Reset',
    refresh: 'Refresh'
  }
}
```

### Form Labels

```javascript
forms: {
  required: 'Required',
  optional: 'Optional',
  email: 'Email',
  password: 'Password',
  name: 'Name'
}
```

### Status Labels

```javascript
status: {
  active: 'Active',
  inactive: 'Inactive',
  pending: 'Pending',
  completed: 'Completed',
  cancelled: 'Cancelled'
}
```

### Error Messages

```javascript
errors: {
  required: 'This field is required',
  invalidEmail: 'Please enter a valid email',
  minLength: 'Must be at least {{min}} characters',
  maxLength: 'Must be at most {{max}} characters'
}
```

---

## Translation Keys Convention

### Naming

- Use camelCase for keys
- Use descriptive names
- Group by feature/domain
- Avoid abbreviations

### Examples

```javascript
// Good
inventory.products.title
inventory.products.actions.create
inventory.products.fields.name

// Bad
inv.prod.ttl
inv.prod.act.crt
inv.prod.fld.nm
```

### Pluralization

```javascript
// English has singular/plural
inventory.products.item: {
  one: '{count} item',
  other: '{count} items'
}

// Some languages have more forms
// Swedish uses same form for all
```

---

## Adding a New Language

### Step 1: Create Locale File

```bash
touch frontend/src/i18n/locales/de.js
```

### Step 2: Copy Structure

```javascript
// i18n/locales/de.js
import en from './en'

// Copy structure from English
export default { ...en }
```

### Step 3: Translate

Replace all English values with translations.

### Step 4: Register in i18n Setup

```javascript
// i18n/index.js
import de from './locales/de'

const i18n = createI18n({
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en,
    sv,
    de  // Add here
  }
})
```

### Step 5: Add Language Option

```javascript
// In app translations
app: {
  language: {
    label: 'Language',
    english: 'English',
    swedish: 'Swedish',
    german: 'German'  // Add here
  }
}
```

---

## Best Practices

1. **Don't hardcode strings** - Always use translation keys
2. **Use descriptive keys** - Keys should explain context
3. **Keep translations updated** - Add new keys promptly
4. **Test all languages** - Switch languages to verify
5. **Consider text length** - German/French text is often longer
6. **Use interpolation** - For dynamic values
7. **Handle plurals** - Use pluralization features

---

## Limitations

- No RTL (Right-to-Left) support
- No dynamic language loading
- No translation management UI
- No auto-translation
- No context-specific translations
- No gender-specific translations
