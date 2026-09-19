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
    page.getByRole("img", { name: "75% authorization readiness" }),
  ).toBeVisible();
  await expect(
    page.getByText("Needs more evidence", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("3 of 4", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Upload the most recent orthopedic physical exam note",
    }),
  ).toBeVisible();
  await expect(page.getByText("$1,200", { exact: false })).toBeVisible();
  await expect(page.getByText("Verified", { exact: true })).toHaveCount(2);
  await page
    .getByRole("button", { name: "Explain Conservative treatment" })
    .click();
  const drawer = page.getByRole("dialog");
  await expect(
    drawer.getByText("PT Progress Note, page 2", { exact: true }),
  ).toBeVisible();
  await expect(
    drawer.getByText("ACL Reconstruction Policy, Section 4.2", { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Explain Conservative treatment" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Review missing evidence" }).click();
  await expect(
    drawer.getByText("No supporting source was identified in this analysis."),
  ).toBeVisible();
  await expect(
    drawer.getByText("Upload the most recent orthopedic physical exam note", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Needs attention 1" }).click();
  await expect(page.getByRole("button", { name: /^Explain / })).toHaveCount(1);
  await page.emulateMedia({ media: "print" });
  await expect(page.getByRole("button", { name: /^Explain / })).toHaveCount(4);
  await page.emulateMedia({ media: "screen" });
  expect(errors).toEqual([]);
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
    page.getByRole("img", { name: "75% authorization readiness" }),
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
    page.getByRole("img", { name: "75% authorization readiness" }),
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
