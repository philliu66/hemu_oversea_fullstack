export default [
  {
    path: '/user',
    layout: false,
    routes: [
      {
        name: 'login',
        path: '/user/login',
        component: './user/login',
      },
    ],
  },
  {
    path: '/callback',
    layout: false,
    name: 'callback',
    component: './callback',
  },
  {
    path: '/welcome',
    name: 'welcome',
    icon: 'smile',
    component: './Welcome',
  },
  {
    path: '/supplier',
    name: 'supplier',
    icon: 'shop',
    routes: [
      {
        path: '/supplier',
        redirect: '/supplier/list',
      },
      {
        path: '/supplier/list',
        name: 'list',
        component: './supplier/list',
      },
      {
        path: '/supplier/create',
        name: 'create',
        component: './supplier/create',
        hideInMenu: true,
      },
      {
        path: '/supplier/detail/:id',
        name: 'detail',
        component: './supplier/detail',
        hideInMenu: true,
      },
      {
        path: '/supplier/edit/:id',
        name: 'edit',
        component: './supplier/edit',
        hideInMenu: true,
      },
    ],
  },
  {
    path: '/store',
    name: 'store',
    icon: 'shopping',
    routes: [
      {
        path: '/store',
        redirect: '/store/list',
      },
      {
        path: '/store/list',
        name: 'list',
        component: './store/list',
      },
      {
        path: '/store/inspection',
        name: 'inspection',
        component: './store/inspection',
      },
      {
        path: '/store/create',
        name: 'create',
        component: './store/create',
        hideInMenu: true,
      },
      {
        path: '/store/detail/:id',
        name: 'detail',
        component: './store/detail',
        hideInMenu: true,
      },
      {
        path: '/store/edit/:id',
        name: 'edit',
        component: './store/edit',
        hideInMenu: true,
      },
    ],
  },
  {
    path: '/product',
    name: 'product',
    icon: 'appstore',
    routes: [
      {
        path: '/product',
        redirect: '/product/list',
      },
      {
        path: '/product/list',
        name: 'list',
        component: './product/list',
      },
      {
        path: '/product/detail/:id',
        name: 'detail',
        component: './product/detail',
        hideInMenu: true,
      },
      {
        path: '/product/category',
        name: 'category',
        component: './product/category',
      },
      {
        path: '/product/seed-category',
        name: 'seedCategory',
        component: './product/seed-category',
      },
    ],
  },
  {
    path: '/personnel',
    name: 'personnel',
    icon: 'team',
    access: 'canSupplierAdmin',
    routes: [
      {
        path: '/personnel',
        redirect: '/personnel/staff',
      },
      {
        path: '/personnel/staff',
        name: 'staff',
        component: './staff/list',
        access: 'canSupplierAdmin',
      },
    ],
  },
  {
    path: '/dev',
    name: 'dev',
    component: './Dev',
    hideInMenu: true,
  },
  {
    path: '/account',
    hideInMenu: true,
    routes: [
      {
        path: '/account/settings',
        name: 'account.settings',
        component: './account/settings',
        hideInMenu: true,
      },
    ],
  },
  {
    path: '/',
    redirect: '/welcome',
  },
  {
    component: './exception/404',
    layout: false,
    path: './*',
  },
];
