import { expect } from '@playwright/test';
import { test } from './fixture';

test('TC-LOGIN-001 登录状态冒烟检查', async ({ page, aiAssert }) => {
  const baseUrl = process.env.TEST_BASE_URL;
  expect(baseUrl, 'TEST_BASE_URL is required').toBeTruthy();

  await page.goto(baseUrl!);
  await page.addStyleTag({
    content: `
      [data-sensitive="true"],
      .phone,
      .email,
      .id-card,
      .token {
        filter: blur(8px) !important;
      }
    `
  });

  await aiAssert('页面已经正常打开，没有显示浏览器错误页、服务端 500 错误或明显白屏');
});

