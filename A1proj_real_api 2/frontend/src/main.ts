import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import App from './App.vue';
import router from './router';
import './assets/styles/global.css';

const THEME_KEY = 'a1proj-theme';
const savedTheme = localStorage.getItem(THEME_KEY);
const preferredTheme = window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
document.documentElement.setAttribute(
  'data-theme',
  savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : preferredTheme
);

const app = createApp(App);

app.use(createPinia());
app.use(ElementPlus);
app.use(router);

app.mount('#app');
