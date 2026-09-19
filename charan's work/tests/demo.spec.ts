import { expect, test } from "@playwright/test";

test("ACL case from setup through source-backed explanation and next action", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("combobox", { name: "Patient case" }),
  ).toHaveValue("P001");
  await page
    .getByRole("button", { name: "Analyze Authorization Readiness" })
    .click();
  await expect(
    page.getByRole("region", { name: "Analyzing authorization readiness" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "71% authorization readiness" }),
  ).toBeVisible();
  await expect(
    page.getByText("Blocked", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("5 of 7", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Confirm the positive Lachman finding",
          exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("$1,450", { exact: false })).toBeVisible();
  await expect(page.getByText("Verified", { exact: true })).toHaveCount(1);
  await page
    .getByRole("button", { name: "Explain Conservative treatment duration" })
    .click();
  const drawer = page.getByRole("dialog");
  await expect(
    drawer.getByText("PT Encounter Timeline, synthetic", { exact: true }),
  ).toBeVisible();
  await expect(
    drawer.getByText("ACL Policy 2026.09, Section 4.3", { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Explain Conservative treatment duration" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Review missing evidence" }).click();
  await expect(
    drawer.getByText("Orthopedic Note, page 1", { exact: true }),
  ).toBeVisible();
  await expect(
    drawer.getByText("Confirm the positive Lachman finding", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Needs attention 2" }).click();
  await expect(page.getByRole("button", { name: /^Explain / })).toHaveCount(2);
  await page.emulateMedia({ media: "print" });
  await expect(page.getByRole("button", { name: /^Explain / })).toHaveCount(7);
  await page.emulateMedia({ media: "screen" });
  expect(errors).toEqual([]);
});

test("Case Guide answers from the current case with source context", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Ask Case Guide" }).click();
  const guide = page.getByRole("dialog", { name: "AccessGraph Case Guide" });
  await expect(guide).toBeVisible();
  await guide.getByRole("button", { name: "What is blocking this case?" }).click();
  await expect(guide.getByText(/5 of 7 criteria are satisfied/)).toBeVisible();
  await expect(
    guide.getByText("PT Encounter Timeline, synthetic", { exact: false }),
  ).toBeVisible();
  await expect(guide.getByText(/does not determine coverage/)).toBeVisible();
  await guide.getByRole("button", { name: "Close Case Guide" }).click();
  await expect(guide).toBeHidden();
});

test("cancel returns to setup and local files do not alter analyzed evidence", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Analyze Authorization Readiness" })
    .click();
  await page.getByRole("button", { name: "Cancel analysis" }).click();
  await expect(
    page.getByRole("combobox", { name: "Patient case" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add / preview" }).click();
  await page.getByLabel("Choose synthetic records").setInputFiles({
    name: "exam.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic local exam note."),
  });
  await page.getByText("Preview text", { exact: true }).click();
  await expect(
    page.getByText("Synthetic local exam note.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Files stay in this browser session", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page
    .getByRole("button", { name: "Analyze Authorization Readiness" })
    .click();
  await expect(
    page.getByRole("img", { name: "71% authorization readiness" }),
  ).toBeVisible();
});

test("mobile flow has no horizontal overflow and explanation remains usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Analyze Authorization Readiness" })
    .click();
  await expect(
    page.getByRole("img", { name: "71% authorization readiness" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Review missing evidence" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Close dialog" }),
  ).toBeInViewport();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "Demo walkthrough" }).click();
  await expect(
    page.getByRole("dialog", { name: "From case to clarity" }),
  ).toBeVisible();
});


test("offline demo enforces human review and verified-agent ordering", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Analyze Authorization Readiness" }).click();
  await page.getByRole("button", { name: "Confirm instability finding" }).click();
  await expect(page.getByText("6 of 7", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Verify PT agent" }).click();
  await expect(page.getByText("Verified", { exact: true })).toHaveCount(2);
  await page.getByRole("button", { name: "Add verified 14-day PT record" }).click();
  await expect(page.getByRole("img", { name: "100% authorization readiness" })).toBeVisible();
  await expect(page.getByText("Case is ready for human review")).toBeVisible();
  await expect(page.getByText(/CASE_READY — all seven requirements satisfied/)).toBeVisible();
});
