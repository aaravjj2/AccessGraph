import { expect, test } from "@playwright/test";
import fixture from "../src/mocks/authorizationResult.json" with { type: "json" };
import request from "../src/mocks/analyzeCaseRequest.json" with { type: "json" };

test("one configuration change uses the real HTTP adapter and canonical payload", async ({
  page,
}) => {
  const calls: unknown[] = [];
  await page.route("**/analyze-case", async (route) => {
    calls.push(route.request().postDataJSON());
    expect(route.request().method()).toBe("POST");
    await route.fulfill({ json: fixture });
  });
  await page.goto("/");
  await expect(
    page.getByText("Connected workspace", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Analyze Authorization Readiness" })
    .click();
  await expect(
    page.getByRole("img", { name: "71% authorization readiness" }),
  ).toBeVisible();
  expect(calls).toEqual([request]);
});

for (const scenario of [
  {
    name: "backend unavailable",
    code: "UNAVAILABLE",
    title: "We couldn’t reach the analysis service",
  },
  {
    name: "missing policy",
    code: "NO_POLICY",
    title: "No policy is available for this case",
  },
  {
    name: "missing clinical evidence",
    code: "NO_CLINICAL_EVIDENCE",
    title: "No clinical evidence was found",
  },
  {
    name: "malformed response",
    code: "MALFORMED",
    title: "The analysis could not be safely displayed",
  },
]) {
  test(`${scenario.name} shows recovery and retains the selected case`, async ({
    page,
  }) => {
    await page.route("**/analyze-case", async (route) => {
      if (scenario.code === "UNAVAILABLE") await route.abort();
      else if (scenario.code === "MALFORMED")
        await route.fulfill({
          json: { ...fixture, authorization_readiness: 8 },
        });
      else await route.fulfill({ status: 422, json: { code: scenario.code } });
    });
    await page.goto("/");
    await page
      .getByRole("button", { name: "Analyze Authorization Readiness" })
      .click();
    await expect(page.getByRole("alert")).toContainText(scenario.title);
    await expect(
      page.getByRole("combobox", { name: "Patient case" }),
    ).toHaveValue("P001");
    await page.route("**/analyze-case", (route) =>
      route.fulfill({ json: fixture }),
    );
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(
      page.getByRole("img", { name: "71% authorization readiness" }),
    ).toBeVisible();
  });
}

test("partial details and unavailable identity are visible without invented citations", async ({
  page,
}) => {
  await page.route("**/analyze-case", (route) =>
    route.fulfill({
      json: {
        ...fixture,
        status: "PARTIAL_ANALYSIS",
        identity_status: {
          provider_agent_verified: false,
          insurer_agent_verified: false,
        },
        explanations: [
          {
            ...fixture.explanations[1],
            patient_evidence: "8 weeks PT documented",
            payer_requirement: "Minimum 6 weeks",
          },
        ],
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Analyze Authorization Readiness" })
    .click();
  await expect(
    page.getByText("Some analysis details are unavailable"),
  ).toBeVisible();
  await expect(page.getByText("Not verified", { exact: true })).toHaveCount(2);
  await page
    .getByRole("button", { name: "Explain Persistent symptoms" })
    .click();
  await expect(
    page.getByText(
      "Clinical source reference not supplied by the analysis service.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Policy source reference not supplied by the analysis service.",
    ),
  ).toBeVisible();
});
