# AccessGraph API Contract

## Policy Agent

The Policy Agent is independently addressable by the Orchestrator only.

```http
POST /policy/extract
Content-Type: application/json
```

Request:

```json
{
  "insurer": "ExampleHealth PPO",
  "procedure": "ACL_RECONSTRUCTION",
  "policy_version": "2026-09",
  "documents": [{
    "source_id": "policy_acl_2026_09",
    "source_label": "ACL Reconstruction Policy",
    "text": "Policy text"
  }]
}
```

Response conforms to `shared/schemas/policy_requirements.schema.json`:

```json
{
  "insurer": "ExampleHealth PPO",
  "procedure": "ACL_RECONSTRUCTION",
  "policy_version": "2026-09",
  "requirements": []
}
```

Every requirement must contain `criterion_id`, `description`, `type`, `required_value`, `source_label`, and `source_location`. The only supported requirement types are `boolean`, `numeric_min`, `numeric_max`, `categorical`, and `text_presence`.

`policy_version` is a string when supplied and `null` when unavailable. Consumers must not infer a version.
