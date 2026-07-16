import { expect, test } from "@playwright/test";

test("sends a message and renders only the user text and final answer", async ({ page }) => {
  await page.goto("/");

  const message = page.getByLabel("Message");
  await message.fill("Which IT laptops in EMEA have not synced in 30 days?");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(
    page.getByText("Which IT laptops in EMEA have not synced in 30 days?"),
  ).toBeVisible();

  const assistantMessage = page.locator("li.message.assistant").last();
  await expect(assistantMessage).toBeVisible({ timeout: 25_000 });
  await expect(assistantMessage.locator("p").first()).not.toBeEmpty();

  // Tool call arguments/results must never reach the transcript DOM.
  const transcriptText = await page.locator(".transcript").innerText();
  expect(transcriptText).not.toContain('"count"');
  expect(transcriptText).not.toContain('"items"');
  expect(transcriptText).not.toContain("tool_rounds");
});

test("a new tab gets a different thread id than an existing one", async ({ browser }) => {
  const contextA = await browser.newContext();
  const pageA = await contextA.newPage();
  await pageA.goto("/");
  const threadA = await pageA.evaluate(() => sessionStorage.getItem("ops-agent.thread-id"));
  await contextA.close();

  const contextB = await browser.newContext();
  const pageB = await contextB.newPage();
  await pageB.goto("/");
  const threadB = await pageB.evaluate(() => sessionStorage.getItem("ops-agent.thread-id"));
  await contextB.close();

  expect(threadA).toBeTruthy();
  expect(threadB).toBeTruthy();
  expect(threadA).not.toBe(threadB);
});
