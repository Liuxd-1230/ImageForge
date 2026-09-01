import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  components,
  directives,
  defaults: {
    VCard: {
      elevation: 0,
      rounded: 'lg',
    },
    VBtn: {
      elevation: 0,
      rounded: 'md',
    },
    VTextField: {
      density: 'compact',
      variant: 'outlined',
      hideDetails: 'auto',
    },
    VTextarea: {
      density: 'compact',
      variant: 'outlined',
      hideDetails: 'auto',
    },
    VSelect: {
      density: 'compact',
      variant: 'outlined',
      hideDetails: 'auto',
    },
    VAutocomplete: {
      density: 'compact',
      variant: 'outlined',
      hideDetails: 'auto',
    },
    VChip: {
      density: 'compact',
      rounded: 'md',
      variant: 'tonal',
    },
    VTable: {
      density: 'compact',
    },
    VDialog: {
      rounded: 'lg',
    },
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#4F46E5', // Indigo 600
          'primary-darken-1': '#4338CA',
          secondary: '#475569', // Slate 600
          surface: '#FFFFFF',
          'surface-variant': '#F8FAFC',
          background: '#F1F5F9',
          outline: '#CBD5E1',
          error: '#DC2626',
          info: '#2563EB',
          success: '#16A34A',
          warning: '#D97706',
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: '#818CF8', // Indigo 400
          'primary-darken-1': '#6366F1',
          secondary: '#94A3B8',
          surface: '#1E222B',
          'surface-variant': '#282D37',
          background: '#12141A',
          outline: '#333946',
          error: '#F87171',
          info: '#60A5FA',
          success: '#4ADE80',
          warning: '#FBBF24',
        },
      },
    },
  },
})
