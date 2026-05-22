export default ({ app, router, store, Vue }) => {
  // Insert a runtime style tag at the end of <head> so it overrides other CSS.
  const css = `
  /* Runtime enforced header and button theming */
  body.q-dark .q-header.ec-header,
  body.body--dark .q-header.ec-header,
  body.q-dark .ec-header,
  body.body--dark .ec-header {
    background-color: var(--ec-surface-700) !important;
    background-image: none !important;
    color: var(--ec-text) !important;
    border-bottom: 1px solid rgba(255,255,255,0.04) !important;
  }

  body:not(.q-dark) .q-header.ec-header,
  body.body--light .q-header.ec-header,
  body:not(.q-dark) .ec-header,
  body.body--light .ec-header {
    background-color: #f3f9f3 !important;
    background-image: none !important;
    color: #0f1720 !important;
    border-bottom: 1px solid rgba(15,23,32,0.06) !important;
  }

  /* Toolbar title, icons and action buttons inside the header inherit readable color */
  body.q-dark .ec-header .q-toolbar-title,
  body.body--dark .ec-header .q-toolbar-title,
  body.q-dark .ec-header .q-btn,
  body.body--dark .ec-header .q-btn,
  body.q-dark .ec-header .q-icon,
  body.body--dark .ec-header .q-icon {
    color: var(--ec-text) !important;
  }

  body:not(.q-dark) .ec-header .q-toolbar-title,
  body.body--light .ec-header .q-toolbar-title,
  body:not(.q-dark) .ec-header .q-btn,
  body.body--light .ec-header .q-btn,
  body:not(.q-dark) .ec-header .q-icon,
  body.body--light .ec-header .q-icon {
    color: #0f1720 !important;
  }

  /* Buttons: remove forced dark backgrounds and ensure icons inherit color */
  .ec-header .q-btn {
    background: transparent !important;
    color: inherit !important;
  }
  .ec-header .q-btn .q-icon {
    color: inherit !important;
  }

  /* Make header title slightly bolder for legibility */
  .ec-header .q-toolbar-title {
    font-weight: 600 !important;
  }
  `

  const style = document.createElement('style')
  style.setAttribute('data-enforced', 'force-header-theme')
  style.appendChild(document.createTextNode(css))
  document.head.appendChild(style)

  // Observe body class changes (theme toggles) to re-apply styles if necessary
  const observer = new MutationObserver(() => {
    // No action required: CSS uses body classes and will update automatically.
    // This keeps the observer alive so the boot file persists in single-page navs.
  })
  observer.observe(document.body, { attributes: true, attributeFilter: ['class'] })
}
