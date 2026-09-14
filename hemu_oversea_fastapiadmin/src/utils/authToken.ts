import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '@/constants/api';

export function getAccessToken(): string {
  if (typeof localStorage === 'undefined') {
    return '';
  }
  return localStorage.getItem(ACCESS_TOKEN_KEY) ?? '';
}

export function getRefreshToken(): string {
  if (typeof localStorage === 'undefined') {
    return '';
  }
  return localStorage.getItem(REFRESH_TOKEN_KEY) ?? '';
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof localStorage === 'undefined') {
    return;
  }
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  if (typeof localStorage === 'undefined') {
    return;
  }
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}
