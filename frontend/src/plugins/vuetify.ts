import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#3F51B5',
          secondary: '#5C6BC0',
          surface: '#FFFFFF',
          background: '#F4F5F7',
          error: '#BA1A1A',
          info: '#0288D1',
          success: '#2E7D32',
          warning: '#ED6C02',
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: '#8C9EFF',
          secondary: '#B0BEC5',
          surface: '#1A1C22',
          background: '#121316',
          error: '#FFB4AB',
          info: '#81D4FA',
          success: '#81C784',
          warning: '#FFD54F',
        },
      },
    },
  },
})
