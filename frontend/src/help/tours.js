// Tour navigation metadata for the interactive click-through walkthroughs.
//
// Each tour is keyed by the matching help article id (e.g. `walkthroughReceivePo`)
// so the "Start click-through" button on a walkthrough article can launch it
// directly. A tour is an ordered list of steps:
//
//   route  – the real app route to navigate to for this step (a path, optionally
//            with a `?tab=` query so the right Settings tab opens). The tour
//            engine pushes this route when the step becomes active so the user
//            lands on the actual screen the instruction is about.
//   target – a CSS selector for the element to spotlight (an element carrying a
//            `data-tour="..."` attribute). When the element is present on the
//            navigated page the overlay highlights it; when it is not found (e.g.
//            it lives inside a dialog that is not open yet) the overlay falls
//            back to a centered coach card so the tour never breaks.
//
// The displayed title/text for each step live in i18n at
// `help.tours.<tourId>.steps[<i>].{title,text}` so they stay in EN/SV parity.
//
// IMPORTANT: the number of steps here MUST match the number of `steps` entries
// in the i18n locale files (see /tmp/validate_help.cjs which checks this).

export const TOURS = {
  walkthroughReceivePo: [
    { route: '/purchase-orders', target: '[data-tour="po-new"]' },
    { route: '/purchase-orders', target: '[data-tour="po-add-line"]' },
    { route: '/purchase-orders', target: '[data-tour="po-save-status"]' },
    { route: '/receive', target: '[data-tour="receive-lookup"]' },
    { route: '/inventory', target: '[data-tour="inventory-list"]' },
  ],
  walkthroughRunJob: [
    { route: '/jobs', target: '[data-tour="jobs-new"]' },
    { route: '/jobs', target: '[data-tour="job-requirements"]' },
    { route: '/jobs', target: '[data-tour="job-status"]' },
    { route: '/jobs', target: '[data-tour="job-scan"]' },
    { route: '/jobs', target: '[data-tour="job-status"]' },
  ],
  walkthroughProductVendor: [
    { route: '/inventory', target: '[data-tour="inventory-new"]' },
    { route: '/inventory', target: '[data-tour="inventory-list"]' },
    { route: '/vendor-catalog', target: '[data-tour="vendor-list"]' },
    { route: '/inventory', target: '[data-tour="inventory-list"]' },
    { route: '/inventory', target: '[data-tour="inventory-list"]' },
  ],
  walkthroughDeliveryRoute: [
    { route: '/route-planner', target: '[data-tour="route-new"]' },
    { route: '/route-planner', target: '[data-tour="route-add-jobs"]' },
    { route: '/route-planner', target: '[data-tour="route-vehicle"]' },
    { route: '/route-planner', target: '[data-tour="route-optimize"]' },
    { route: '/route-planner', target: '[data-tour="route-preview"]' },
  ],
  walkthroughPrintLabels: [
    { route: '/labels', target: '[data-tour="labels-template"]' },
    { route: '/labels', target: '[data-tour="labels-select"]' },
    { route: '/labels', target: '[data-tour="labels-visibility"]' },
    { route: '/labels', target: '[data-tour="labels-print"]' },
  ],
  walkthroughEntraSso: [
    { route: '/settings?tab=auth', target: '[data-tour="settings-sso-enable"]' },
    { route: '/settings?tab=auth', target: '[data-tour="settings-sso-add-oidc"]' },
    { route: '/settings?tab=auth', target: '[data-tour="settings-sso-card"]' },
    { route: '/settings?tab=auth', target: '[data-tour="settings-sso-add-saml"]' },
    { route: '/settings?tab=auth', target: '[data-tour="settings-sso-card"]' },
  ],
  walkthroughOnboardCrew: [
    { route: '/persons', target: '[data-tour="persons-new"]' },
    { route: '/persons', target: '[data-tour="persons-list"]' },
    { route: '/persons', target: '[data-tour="persons-list"]' },
    { route: '/jobs', target: '[data-tour="jobs-list"]' },
    { route: '/persons', target: '[data-tour="persons-list"]' },
  ],
}

// Article ids that have an interactive click-through tour.
export const TOUR_IDS = Object.keys(TOURS)
