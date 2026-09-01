import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

/**
 * ImageForge — Material 3 Expressive (Google Pixel / Gemini direction)
 *
 * Tonal surface palette built on the M3 baseline with a violet-leaning
 * primary. Sections in the Studio express hierarchy through surface tone
 * + spacing + typography instead of outline borders.
 */
export default createVuetify({
  components,
  directives,
  defaults: {
    VCard: {
      elevation: 0,
      rounded: 'xl',
    },
    VBtn: {
      elevation: 0,
      rounded: 'pill',
    },
    VTextField: {
      variant: 'outlined',
      hideDetails: 'auto',
    },
    VTextarea: {
      variant: 'outlined',
      hideDetails: 'auto',
    },
    VSelect: {
      variant: 'outlined',
      hideDetails: 'auto',
    },
    VAutocomplete: {
      variant: 'outlined',
      hideDetails: 'auto',
    },
    VDialog: {
      rounded: 'xl',
    },
    VMenu: {
      rounded: 'lg',
    },
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          // Brand / Primary (violet, slightly blue-shifted)
          primary: '#6750A4',
          'primary-darken-1': '#5A438F',
          'primary-container': '#EADDFF',
          'on-primary-container': '#21005D',
          secondary: '#625B71',
          'secondary-container': '#E8DEF8',
          'on-secondary-container': '#1D192B',
          tertiary: '#7D5260',
          'tertiary-container': '#FFD8E4',
          'on-tertiary-container': '#31111D',

          // Tonal surfaces (user-specified baseline)
          background: '#F9F7FC',
          surface: '#FFFBFF',
          'surface-bright': '#FFFBFF',
          'surface-light': '#FFFBFF',
          'surface-variant': '#F6F2FA',
          'surface-container-lowest': '#FFFFFF',
          'surface-container-low': '#F6F2FA',
          'surface-container': '#F0EBF5',
          'surface-container-high': '#E9E3EF',
          'surface-container-highest': '#E4DEEA',

          // Text
          'on-background': '#1D1B20',
          'on-surface': '#1D1B20',
          'on-surface-variant': '#625F68',
          'text-muted': '#938F99',

          // Structure
          outline: '#CAC4D0',
          'outline-variant': '#E2DCE6',
          'surface-tint': '#6750A4',

          // Status
          error: '#BA1A1A',
          'error-container': '#FFDAD6',
          info: '#00639B',
          success: '#386A20',
          warning: '#8A5700',
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: '#D0BCFF',
          'primary-darken-1': '#B8A4FF',
          'primary-container': '#4F378B',
          'on-primary-container': '#EADDFF',
          secondary: '#CCC2DC',
          'secondary-container': '#4A4458',
          'on-secondary-container': '#E8DEF8',
          tertiary: '#EFB8C8',
          'tertiary-container': '#633B48',
          'on-tertiary-container': '#FFD8E4',

          background: '#141218',
          surface: '#141218',
          'surface-bright': '#3B383E',
          'surface-light': '#1D1B20',
          'surface-variant': '#49454F',
          'surface-container-lowest': '#0F0D13',
          'surface-container-low': '#1D1B20',
          'surface-container': '#211F26',
          'surface-container-high': '#2B2930',
          'surface-container-highest': '#36343B',

          'on-background': '#E6E0E9',
          'on-surface': '#E6E0E9',
          'on-surface-variant': '#CAC4D0',
          'text-muted': '#938F99',

          outline: '#938F99',
          'outline-variant': '#49454F',
          'surface-tint': '#D0BCFF',

          error: '#F2B8B5',
          'error-container': '#8C1D18',
          info: '#83C1E8',
          success: '#9CD49C',
          warning: '#FFD24D',
        },
      },
    },
  },
})
