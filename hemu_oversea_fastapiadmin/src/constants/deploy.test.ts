import { describe, expect, it } from 'vitest';
import {
  APP_BASE,
  APP_LOGIN_PATH,
  APP_PUBLIC_PATH,
  isAppRoutePath,
  stripAppBase,
  withAppBase,
} from './deploy';

describe('deploy path helpers', () => {
  it('exposes /admin base constants', () => {
    expect(APP_BASE).toBe('/admin');
    expect(APP_PUBLIC_PATH).toBe('/admin/');
    expect(APP_LOGIN_PATH).toBe('/user/login');
  });

  it('withAppBase prefixes route paths once', () => {
    expect(withAppBase('/')).toBe('/admin/');
    expect(withAppBase('/user/login')).toBe('/admin/user/login');
    expect(withAppBase('/admin/user/login')).toBe('/admin/user/login');
    expect(withAppBase('/admin')).toBe('/admin/');
  });

  it('stripAppBase removes deploy prefix', () => {
    expect(stripAppBase('/admin')).toBe('/');
    expect(stripAppBase('/admin/')).toBe('/');
    expect(stripAppBase('/admin/user/login')).toBe('/user/login');
    expect(stripAppBase('/user/login')).toBe('/user/login');
  });

  it('isAppRoutePath matches browser path against route path', () => {
    expect(isAppRoutePath('/admin/user/login', APP_LOGIN_PATH)).toBe(true);
    expect(isAppRoutePath('/user/login', APP_LOGIN_PATH)).toBe(true);
    expect(isAppRoutePath('/admin/welcome', APP_LOGIN_PATH)).toBe(false);
  });
});
