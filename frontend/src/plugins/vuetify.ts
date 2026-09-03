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

      /* ══════════════════════════════════════════════════════════════
         Gemini（Neural Expressive 方向）
         亮：#F0F4F8 灰白底 + 白面 + 极淡描边，Google Blue 只做克制强调
         暗：浓郁近黑 + 浅蓝强调；描边与层级用中性灰（无紫调）
         ══════════════════════════════════════════════════════════════ */
      geminiLight: {
        dark: false,
        colors: {
          primary: '#0B57D0',
          'primary-darken-1': '#0A49B0',
          'primary-container': '#D3E3FD',
          'on-primary-container': '#041E49',
          secondary: '#444746',
          'secondary-container': '#E1E3E6',
          'on-secondary-container': '#1B1C1E',
          tertiary: '#5F6368',
          'tertiary-container': '#E8EAED',
          'on-tertiary-container': '#1F1F1F',

          background: '#F0F4F8',
          surface: '#FFFFFF',
          'surface-bright': '#FFFFFF',
          'surface-light': '#F8FAFD',
          'surface-variant': '#EDF1F7',
          'surface-container-lowest': '#FFFFFF',
          'surface-container-low': '#F4F7FB',
          'surface-container': '#EAEFF6',
          'surface-container-high': '#E1E8F1',
          'surface-container-highest': '#D7E0EC',

          'on-background': '#1F1F1F',
          'on-surface': '#1F1F1F',
          'on-surface-variant': '#444746',
          'text-muted': '#5F6368',

          outline: '#747775',
          'outline-variant': '#E1E4EA',
          'surface-tint': '#0B57D0',

          error: '#B3261E',
          'error-container': '#F9DEDC',
          info: '#0B57D0',
          success: '#146C2E',
          warning: '#8A5700',
        },
      },
      geminiDark: {
        dark: true,
        colors: {
          primary: '#A8C7FA',
          'primary-darken-1': '#8FB7F8',
          'primary-container': '#0B3C6B',
          'on-primary-container': '#D3E3FD',
          secondary: '#C4C7C5',
          'secondary-container': '#444746',
          'on-secondary-container': '#E3E3E3',
          tertiary: '#9AA0A6',
          'tertiary-container': '#3C4043',
          'on-tertiary-container': '#E8EAED',

          background: '#131314',
          surface: '#1E1F20',
          'surface-bright': '#3B3C3E',
          'surface-light': '#262728',
          'surface-variant': '#444746',
          'surface-container-lowest': '#0E0E0F',
          'surface-container-low': '#1E1F20',
          'surface-container': '#262728',
          'surface-container-high': '#2F3031',
          'surface-container-highest': '#3A3B3D',

          'on-background': '#E3E3E3',
          'on-surface': '#E3E3E3',
          'on-surface-variant': '#C4C7C5',
          'text-muted': '#8E918F',

          outline: '#8E918F',
          'outline-variant': '#444746',
          'surface-tint': '#A8C7FA',

          error: '#F2B8B5',
          'error-container': '#8C1D18',
          info: '#A8C7FA',
          success: '#9CD49C',
          warning: '#FFD24D',
        },
      },

      /* ══════════════════════════════════════════════════════════════
         Antigravity（极简黑白灰方向）
         亮：纯白底 + 中性灰面 + #121317 近黑主操作（黑药丸按钮）
         暗：#121317 木烟黑 + 白色主操作；全站无彩色 hue
         ══════════════════════════════════════════════════════════════ */
      antigravityLight: {
        dark: false,
        colors: {
          primary: '#121317',
          'primary-darken-1': '#000000',
          'primary-container': '#E8E8EC',
          'on-primary-container': '#121317',
          secondary: '#45474D',
          'secondary-container': '#EFEFEF',
          'on-secondary-container': '#121317',
          tertiary: '#6E6E73',
          'tertiary-container': '#E8E8EC',
          'on-tertiary-container': '#121317',

          background: '#FFFFFF',
          surface: '#FFFFFF',
          'surface-bright': '#FFFFFF',
          'surface-light': '#F7F7F9',
          'surface-variant': '#F0F0F3',
          'surface-container-lowest': '#FFFFFF',
          'surface-container-low': '#F7F7F9',
          'surface-container': '#F0F0F3',
          'surface-container-high': '#E8E8EC',
          'surface-container-highest': '#DFDFE4',

          'on-background': '#121317',
          'on-surface': '#121317',
          'on-surface-variant': '#45474D',
          'text-muted': '#8A8A92',

          outline: '#C7C7CC',
          'outline-variant': '#E7E7EB',
          'surface-tint': '#121317',

          error: '#B3261E',
          'error-container': '#F9DEDC',
          info: '#45474D',
          success: '#146C2E',
          warning: '#8A5700',
        },
      },
      antigravityDark: {
        dark: true,
        colors: {
          primary: '#F2F2F5',
          'primary-darken-1': '#D8D8DE',
          'primary-container': '#2A2B33',
          'on-primary-container': '#F2F2F5',
          secondary: '#A9AAB2',
          'secondary-container': '#26272D',
          'on-secondary-container': '#F2F2F5',
          tertiary: '#A9AAB2',
          'tertiary-container': '#32333C',
          'on-tertiary-container': '#F2F2F5',

          background: '#121317',
          surface: '#121317',
          'surface-bright': '#32333C',
          'surface-light': '#1C1D22',
          'surface-variant': '#2E2F38',
          'surface-container-lowest': '#0C0D10',
          'surface-container-low': '#1C1D22',
          'surface-container': '#22232A',
          'surface-container-high': '#2A2B33',
          'surface-container-highest': '#32333C',

          'on-background': '#F2F2F5',
          'on-surface': '#F2F2F5',
          'on-surface-variant': '#A9AAB2',
          'text-muted': '#6E6F78',

          outline: '#5C5D66',
          'outline-variant': '#2E2F38',
          'surface-tint': '#F2F2F5',

          error: '#F2B8B5',
          'error-container': '#8C1D18',
          info: '#A9AAB2',
          success: '#9CD49C',
          warning: '#FFD24D',
        },
      },
    },
  },
})
