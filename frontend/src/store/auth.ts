import { ref } from "vue";

const ACCESS_TOKEN_KEY = "access_token";
const accessToken = ref<string | null>(localStorage.getItem(ACCESS_TOKEN_KEY));

window.addEventListener("storage", (event) => {
  if (event.key === ACCESS_TOKEN_KEY) {
    accessToken.value = event.newValue;
  }
});

export function getAccessToken() {
  return accessToken.value;
}

export function isAuthenticated() {
  return Boolean(accessToken.value);
}

export function saveToken(token: string) {
  accessToken.value = token;
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearToken() {
  accessToken.value = null;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}
