"""
Helios FAQ RAG Pipeline — single-file submission
Usage: python helios-rag-single.py
Env:   TEST_INPUTS_PATH, RESULTS_PATH, ANTHROPIC_API_KEY
"""

import json, os, re, math, urllib.request

# ── Paths ────────────────────────────────────────────────────────────────────
TEST_INPUTS_PATH = os.environ.get("TEST_INPUTS_PATH", "/workspace/test_inputs.json")
RESULTS_PATH     = os.environ.get("RESULTS_PATH",     "/workspace/results.json")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL    = "claude-sonnet-4-20250514"
TOP_K    = 5
MAX_TOKENS = 512

# ── Inline dataset (200 Helios FAQ entries) ──────────────────────────────────
DATASET_JSON = r"""[
  {
    "id": "faq-001",
    "category": "Billing",
    "question": "How do I update the credit card for my workspace?",
    "answer": "Workspace owners can update payment details from Settings > Billing > Payment method. The new card is used for the next invoice and any outstanding balance is retried automatically within one hour. Members without owner access can view neither the full card number nor the billing page."
  },
  {
    "id": "faq-002",
    "category": "Billing",
    "question": "Can I switch from monthly billing to annual billing?",
    "answer": "Yes. Go to Settings > Billing > Plan and choose Annual billing. Helios prorates the current month and applies the annual price immediately, so the next invoice shows both the credit and the yearly charge."
  },
  {
    "id": "faq-003",
    "category": "Billing",
    "question": "Where can I download invoices for Helios?",
    "answer": "Invoices are available under Settings > Billing > Invoices. Owners and billing admins can download PDF invoices and CSV receipts for each billing period. If you need the invoice emailed automatically, add a billing contact on the same page."
  },
  {
    "id": "faq-004",
    "category": "Billing",
    "question": "What happens if a payment fails?",
    "answer": "Helios sends payment failure notices to owners and billing contacts. The workspace remains active during a 14 day grace period while the card is retried. If payment is still unresolved after the grace period, project editing is paused until the balance is paid."
  },
  {
    "id": "faq-005",
    "category": "Billing",
    "question": "Do guests count toward paid seats?",
    "answer": "Guests do not count as paid seats when they only access projects they were invited to. If a guest is added to a team, assigned workspace-level permissions, or joins more than three projects, Helios converts them to a billable member. Owners receive a notice before the next invoice includes the seat."
  },
  {
    "id": "faq-006",
    "category": "Billing",
    "question": "Can I add a purchase order number to invoices?",
    "answer": "Yes. Owners and billing admins can add a purchase order number in Settings > Billing > Invoice details. The value appears on future invoices, but past invoices are not regenerated automatically. Contact support if an older invoice needs to be reissued."
  },
  {
    "id": "faq-007",
    "category": "Getting Started",
    "question": "What is the fastest way to set up a new Helios workspace?",
    "answer": "Create a workspace, invite your core team, and start with one project template rather than building every workflow at once. The onboarding checklist walks owners through teams, statuses, cycles, and notification defaults. Most teams can get their first project running in under 20 minutes."
  },
  {
    "id": "faq-008",
    "category": "Getting Started",
    "question": "How do I import tasks from a spreadsheet?",
    "answer": "Open the project, choose Import, and upload a CSV file with title, description, status, assignee, and due date columns. Helios previews the mapping before anything is created. Rows with missing titles are skipped and shown in the import report."
  },
  {
    "id": "faq-009",
    "category": "Getting Started",
    "question": "Can I use templates for recurring projects?",
    "answer": "Yes. Any owner or project admin can save a project as a template. Templates preserve sections, custom fields, statuses, and default tasks, but they do not copy comments or private attachments. You can use a template when creating a new project or quarterly plan."
  },
  {
    "id": "faq-010",
    "category": "Getting Started",
    "question": "How are projects, teams, and tasks related?",
    "answer": "Teams contain members and shared workflow settings. Projects belong to a team and group related tasks around a goal or delivery plan. Tasks are the individual work items that can have owners, due dates, dependencies, comments, and attachments."
  },
  {
    "id": "faq-011",
    "category": "Getting Started",
    "question": "Can I create tasks by email?",
    "answer": "Yes. Each project has an inbound email address under Project settings > Email intake. Messages sent to that address become new tasks with the subject as the title and the email body as the description. Attachments under 25 MB are included automatically."
  },
  {
    "id": "faq-012",
    "category": "Getting Started",
    "question": "What should I do after inviting my team?",
    "answer": "After invites are sent, configure default statuses and create one project that matches your team's real workflow. Ask members to claim or update their first tasks during the kickoff. This helps Helios learn useful notification and assignment patterns."
  },
  {
    "id": "faq-013",
    "category": "Integrations",
    "question": "Does Helios integrate with Slack?",
    "answer": "Yes. The Slack integration can post project updates, task assignments, mentions, and due date reminders to selected channels. Each user can also connect Slack for personal notifications. Workspace owners control which Slack workspace is authorized."
  },
  {
    "id": "faq-014",
    "category": "Integrations",
    "question": "How do I connect GitHub to Helios?",
    "answer": "Owners can connect GitHub from Settings > Integrations > GitHub. After installation, teams can link repositories to projects and mention pull requests in task comments. Closing a linked pull request can optionally move the task to Done."
  },
  {
    "id": "faq-015",
    "category": "Integrations",
    "question": "Can I sync Helios due dates to Google Calendar?",
    "answer": "Yes. Each user can enable calendar sync from Personal settings > Calendar. Helios creates read-only calendar events for tasks with due dates and milestones. Updates usually appear in Google Calendar within a few minutes."
  },
  {
    "id": "faq-016",
    "category": "Integrations",
    "question": "Does Helios support webhooks?",
    "answer": "Helios supports outgoing webhooks for task created, task updated, comment added, project archived, and status changed events. Webhooks can be configured per workspace or per project. Each delivery includes an HMAC signature so your service can verify it came from Helios."
  },
  {
    "id": "faq-017",
    "category": "Integrations",
    "question": "Can I connect multiple GitHub organizations?",
    "answer": "Yes. A workspace can connect more than one GitHub organization if an owner has installation rights in each organization. Repository access remains limited to the repositories approved during installation. Teams can choose which connected repositories are visible in each project."
  },
  {
    "id": "faq-018",
    "category": "Integrations",
    "question": "Why are Slack notifications not appearing?",
    "answer": "First check that the Slack integration is still connected under Settings > Integrations. Then confirm the project is mapped to the expected channel and that the event type is enabled. If only one user is affected, they should reconnect Slack from Personal settings."
  },
  {
    "id": "faq-019",
    "category": "Account Management",
    "question": "How do I change my email address?",
    "answer": "Open Personal settings > Profile and add the new email address. Helios sends a verification link before the address can become primary. Single sign-on users may need their identity provider admin to update the email instead."
  },
  {
    "id": "faq-020",
    "category": "Account Management",
    "question": "Can I be a member of multiple workspaces?",
    "answer": "Yes. A single Helios account can belong to multiple workspaces. Use the workspace switcher in the top-left corner to move between them. Notifications and billing are managed separately for each workspace."
  },
  {
    "id": "faq-021",
    "category": "Account Management",
    "question": "How do I deactivate a user?",
    "answer": "Workspace owners can deactivate a user from Settings > Members. Deactivation immediately removes login access but keeps their task history, comments, and audit events. Open tasks assigned to the user can be reassigned during the deactivation flow."
  },
  {
    "id": "faq-022",
    "category": "Account Management",
    "question": "Can I transfer workspace ownership?",
    "answer": "Yes. The current owner can transfer ownership from Settings > Members by selecting another active admin. The new owner must accept the transfer before it takes effect. Billing contacts are not changed automatically."
  },
  {
    "id": "faq-023",
    "category": "Account Management",
    "question": "How do I reset my password?",
    "answer": "Use the Forgot password link on the sign-in page. Helios sends a reset link that expires after 30 minutes. If your workspace requires SSO, you must reset the password through your identity provider."
  },
  {
    "id": "faq-024",
    "category": "Account Management",
    "question": "What happens to tasks when someone leaves the company?",
    "answer": "Their tasks, comments, and attachments remain in Helios after the account is deactivated. During deactivation, owners can bulk reassign open tasks to another member. Completed task history continues to show the original contributor."
  },
  {
    "id": "faq-025",
    "category": "Permissions & Roles",
    "question": "What roles are available in Helios?",
    "answer": "Helios includes owner, admin, member, project admin, and guest roles. Owners manage billing, security, and workspace deletion. Admins manage most workspace settings, while project admins control project-level configuration."
  },
  {
    "id": "faq-026",
    "category": "Permissions & Roles",
    "question": "Can guests comment on tasks?",
    "answer": "Guests can comment on tasks inside projects where they have been invited. They cannot see private projects, billing settings, workspace members, or projects outside their invitation. Project admins can disable guest comments for sensitive projects."
  },
  {
    "id": "faq-027",
    "category": "Permissions & Roles",
    "question": "Who can create private projects?",
    "answer": "Owners and admins can always create private projects. Members can create private projects only if the workspace setting allows member-created projects. Guests cannot create projects."
  },
  {
    "id": "faq-028",
    "category": "Permissions & Roles",
    "question": "Can I restrict custom field editing?",
    "answer": "Yes. Project admins can choose whether custom fields are editable by all project members or only project admins. Required fields still appear to members when they create tasks. Field configuration changes are recorded in the project activity log."
  },
  {
    "id": "faq-029",
    "category": "Permissions & Roles",
    "question": "Who can delete a workspace?",
    "answer": "Only the workspace owner can delete a Helios workspace. Deletion requires typing the workspace slug and confirming by email. Admins can archive projects but cannot delete the entire workspace."
  },
  {
    "id": "faq-030",
    "category": "Permissions & Roles",
    "question": "Can members invite new users?",
    "answer": "Owners can choose whether members may invite users from Settings > Security. If member invites are disabled, only owners and admins can send invitations. Guest invitations can be restricted separately at the project level."
  },
  {
    "id": "faq-031",
    "category": "Notifications",
    "question": "How do I turn off email notifications?",
    "answer": "Open Personal settings > Notifications and disable the email events you do not want. You can turn off all email notifications or keep only direct mentions and assignments. Workspace-required security emails cannot be disabled."
  },
  {
    "id": "faq-032",
    "category": "Notifications",
    "question": "Can I get reminders before a task is due?",
    "answer": "Yes. Personal notification settings let you choose reminders one day, three days, or one week before a due date. Reminders can be sent by email, Slack, or in-app notification depending on your connected channels. Tasks without due dates do not trigger reminders."
  },
  {
    "id": "faq-033",
    "category": "Notifications",
    "question": "Why did I receive a notification for a task I do not own?",
    "answer": "Helios notifies you when you are mentioned, subscribed, assigned as a reviewer, or part of a team watching the project. You can unsubscribe from an individual task using the bell icon. Project admins can also adjust default watchers for new tasks."
  },
  {
    "id": "faq-034",
    "category": "Notifications",
    "question": "Can project admins control notification defaults?",
    "answer": "Yes. Project admins can set default watchers, milestone digest settings, and status-change announcements for each project. Individual users can still reduce personal email or Slack delivery. Required security and access-change alerts are always sent."
  },
  {
    "id": "faq-035",
    "category": "Notifications",
    "question": "Does Helios support daily digest emails?",
    "answer": "Yes. Daily digests summarize overdue tasks, upcoming due dates, new mentions, and project changes. Users can choose the delivery time in Personal settings. Digests are skipped on days when there is no relevant activity."
  },
  {
    "id": "faq-036",
    "category": "Notifications",
    "question": "Can I mute a project temporarily?",
    "answer": "Yes. Use the project bell menu and choose Mute for a period such as one day, one week, or until manually restored. Muting suppresses non-critical project notifications. Direct mentions and security alerts still reach you."
  },
  {
    "id": "faq-037",
    "category": "Data & Privacy",
    "question": "Where is Helios data hosted?",
    "answer": "Helios hosts production data in encrypted cloud regions in the United States and European Union. Workspace owners choose the data region during workspace creation on supported plans. Backups stay within the selected region."
  },
  {
    "id": "faq-038",
    "category": "Data & Privacy",
    "question": "Can I export all workspace data?",
    "answer": "Owners can request a full workspace export from Settings > Data export. The export includes projects, tasks, comments, custom fields, attachments metadata, audit logs, and member lists. Large exports may take several hours and are delivered as a secure download link."
  },
  {
    "id": "faq-039",
    "category": "Data & Privacy",
    "question": "How long are deleted tasks retained?",
    "answer": "Deleted tasks remain recoverable for 30 days from the project trash. After 30 days, they are permanently removed from active systems and later age out of encrypted backups. Owners can shorten retention on Enterprise plans."
  },
  {
    "id": "faq-040",
    "category": "Data & Privacy",
    "question": "Does Helios encrypt attachments?",
    "answer": "Yes. Attachments are encrypted at rest and in transit. Access to an attachment is checked against the task and project permissions before download. Public attachment links are not created unless a user explicitly shares one."
  },
  {
    "id": "faq-041",
    "category": "Data & Privacy",
    "question": "Can we sign a data processing agreement?",
    "answer": "Yes. Helios provides a standard data processing agreement for teams on Business and Enterprise plans. Owners can request it from Settings > Data & Privacy. Enterprise customers may route the agreement through their procurement workflow."
  },
  {
    "id": "faq-042",
    "category": "Data & Privacy",
    "question": "Can admins view private project content?",
    "answer": "Workspace owners can view and manage all projects for compliance and recovery. Admins can see private project metadata but need to be added to view task content unless owner override is enabled. All access to private projects is logged."
  },
  {
    "id": "faq-043",
    "category": "Troubleshooting",
    "question": "Why can't I upload an attachment?",
    "answer": "Check that the file is under the workspace attachment limit and that your project role allows uploads. Helios supports most common document, image, and archive formats but blocks executable files. If the upload stalls, try again after disabling browser extensions that intercept file uploads."
  },
  {
    "id": "faq-044",
    "category": "Troubleshooting",
    "question": "Why is search not finding a task I can see?",
    "answer": "Search indexing can take a few minutes after a task is created or heavily edited. Confirm that your filters are not excluding archived projects or completed tasks. If the task is private, only members with project access can find it in search."
  },
  {
    "id": "faq-045",
    "category": "Troubleshooting",
    "question": "What should I do if the app feels slow?",
    "answer": "Start by checking the Helios status page and your browser console for network errors. Large projects with thousands of visible tasks may load faster when filtered by status or assignee. If the issue continues, send support the workspace slug and an approximate timestamp."
  },
  {
    "id": "faq-046",
    "category": "Troubleshooting",
    "question": "Why did my CSV import fail?",
    "answer": "CSV imports fail most often because required title values are missing, date columns use an unsupported format, or the file is larger than 10 MB. Helios shows a row-level error report after the preview step. Fix the listed rows and upload the CSV again."
  },
  {
    "id": "faq-047",
    "category": "Troubleshooting",
    "question": "Why can't I see a project someone mentioned?",
    "answer": "The project may be private, archived, or in a different workspace. Ask a project admin to confirm your membership and whether guest access is allowed. Mentions do not grant access automatically."
  },
  {
    "id": "faq-048",
    "category": "Troubleshooting",
    "question": "How do I recover an archived project?",
    "answer": "Project admins can restore archived projects from Workspace search by filtering for archived projects. Restoring returns the project to its previous team and preserves tasks, comments, and custom fields. Deleted projects require owner support within the retention window."
  },
  {
    "id": "faq-049",
    "category": "Billing",
    "question": "How are seat changes prorated for a small team?",
    "answer": "When seats are added or removed mid-cycle, Helios prorates the change to the day it happened. Added seats are charged on the next invoice, and removed seats create a credit for unused time. Annual plans show the adjustment as a line item."
  },
  {
    "id": "faq-050",
    "category": "Getting Started",
    "question": "Can I create a project from an existing one for a small team?",
    "answer": "Yes. Use Duplicate project from the project menu. Helios copies sections, open tasks, custom fields, and dependencies, but it does not copy private comments by default. You can choose whether assignees and due dates are preserved."
  },
  {
    "id": "faq-051",
    "category": "Integrations",
    "question": "Does Helios have an API for a small team?",
    "answer": "Yes. Helios provides a REST API for tasks, projects, users, comments, and custom fields. API tokens are created in Personal settings and inherit the user's permissions. Enterprise workspaces can restrict token creation."
  },
  {
    "id": "faq-052",
    "category": "Account Management",
    "question": "Can I enable single sign-on for a small team?",
    "answer": "Business and Enterprise workspaces can enable SAML single sign-on from Settings > Security. Owners should test SSO with optional enforcement before requiring it for everyone. SCIM provisioning is available on Enterprise plans."
  },
  {
    "id": "faq-053",
    "category": "Permissions & Roles",
    "question": "Can I make a project read-only for a small team?",
    "answer": "Project admins can set a project to read-only from Project settings > Access. Members can still view tasks and comments, but only project admins can edit content. Read-only mode is useful after a launch or audit period."
  },
  {
    "id": "faq-054",
    "category": "Notifications",
    "question": "Can I route notifications to different Slack channels for a small team?",
    "answer": "Yes. Project admins can choose a Slack channel for each project and select which events are posted there. Personal Slack notifications still go to the user's direct messages. Channel routing requires the workspace Slack integration."
  },
  {
    "id": "faq-055",
    "category": "Data & Privacy",
    "question": "Can I delete my personal account for a small team?",
    "answer": "You can request account deletion from Personal settings > Privacy. Helios removes personal profile data after verifying that you do not own an active workspace. Your historical comments may remain attributed to a deactivated user for audit integrity."
  },
  {
    "id": "faq-056",
    "category": "Troubleshooting",
    "question": "Why can't I assign a task to someone for a small team?",
    "answer": "The person must be an active member or invited guest with access to the project. Deactivated users and users outside the project cannot be assigned new work. If the project is private, add the person to the project first."
  },
  {
    "id": "faq-057",
    "category": "Billing",
    "question": "Can I set a separate billing contact for a small team?",
    "answer": "Yes. Owners can add billing contacts in Settings > Billing > Contacts. Billing contacts receive invoices, payment notices, and renewal reminders, but they do not gain access to projects unless they are also workspace members."
  },
  {
    "id": "faq-058",
    "category": "Getting Started",
    "question": "How do task dependencies work for a small team?",
    "answer": "A task can be blocked by one or more other tasks. Blocked tasks show a dependency warning until the blocking work is completed. Helios does not automatically change due dates, but timeline views highlight conflicts."
  },
  {
    "id": "faq-059",
    "category": "Integrations",
    "question": "Can I connect Jira to Helios for a small team?",
    "answer": "The Jira importer can migrate projects, epics, issues, comments, and basic custom fields into Helios. Continuous two-way Jira sync is not currently supported. Teams that still use Jira can link back to source issues in task descriptions."
  },
  {
    "id": "faq-060",
    "category": "Account Management",
    "question": "How do I change my display name or avatar for a small team?",
    "answer": "Open Personal settings > Profile to update your display name, title, timezone, and avatar. Avatar changes may take a few minutes to appear in mentions and activity feeds. SSO-managed profile fields may be locked."
  },
  {
    "id": "faq-061",
    "category": "Permissions & Roles",
    "question": "Who can manage integrations for a small team?",
    "answer": "Owners and admins can install or remove workspace integrations. Project admins can configure project-level mappings for integrations that are already installed. Members can connect personal integrations such as calendar sync when allowed."
  },
  {
    "id": "faq-062",
    "category": "Notifications",
    "question": "Why am I not getting due date reminders for a small team?",
    "answer": "Due date reminders require a due date, an enabled reminder window, and at least one active delivery channel. Muted projects suppress normal reminders unless you are directly assigned. Check Personal settings > Notifications before contacting support."
  },
  {
    "id": "faq-063",
    "category": "Data & Privacy",
    "question": "Does Helios maintain audit logs for a small team?",
    "answer": "Business and Enterprise plans include audit logs for sign-ins, permission changes, exports, integration changes, and workspace settings. Owners can search and export audit logs from Settings > Security. Audit log retention depends on the plan."
  },
  {
    "id": "faq-064",
    "category": "Troubleshooting",
    "question": "Why are GitHub links not updating tasks for a small team?",
    "answer": "Confirm that the repository is linked to the project and that the pull request mentions the Helios task ID. Some automation requires the GitHub app to have access to the repository. Reinstalling the GitHub integration can fix missing webhook permissions."
  },
  {
    "id": "faq-065",
    "category": "Billing",
    "question": "Is there a free trial for a small team?",
    "answer": "New workspaces start with a 14 day trial of the Business plan. You do not need a credit card to start the trial. If no plan is selected when the trial ends, the workspace moves to the Free plan with Free plan limits."
  },
  {
    "id": "faq-066",
    "category": "Getting Started",
    "question": "Can I use cycles or sprints for a small team?",
    "answer": "Yes. Teams can enable cycles from Team settings. Cycles group tasks into fixed planning windows and provide progress, carryover, and scope-change reporting. Projects can use cycles alongside milestones."
  },
  {
    "id": "faq-067",
    "category": "Integrations",
    "question": "Does the Google Drive integration attach files for a small team?",
    "answer": "Yes. Users can attach Google Drive files to tasks after connecting their Google account. Helios stores a permission-checked link rather than copying the file contents. Drive permissions still control who can open the document."
  },
  {
    "id": "faq-068",
    "category": "Account Management",
    "question": "Can I restore a deactivated user for a small team?",
    "answer": "Owners can reactivate a user from Settings > Members if the account was deactivated rather than deleted. Reactivation restores access to the same teams and projects unless those permissions were changed separately. The user may need to reset their password."
  },
  {
    "id": "faq-069",
    "category": "Permissions & Roles",
    "question": "Can roles be assigned by team for a small team?",
    "answer": "Yes. A member can be a project admin in one team and a regular member in another. Workspace owner and admin roles still apply across the entire workspace. Guest access remains limited to invited projects."
  },
  {
    "id": "faq-070",
    "category": "Notifications",
    "question": "Can I subscribe to a task without commenting for a small team?",
    "answer": "Yes. Select the bell icon on any task to subscribe. Subscribers receive updates for comments, status changes, and due date changes. You can unsubscribe from the same menu later."
  },
  {
    "id": "faq-071",
    "category": "Data & Privacy",
    "question": "Can attachments be restricted by file type for a small team?",
    "answer": "Enterprise owners can restrict attachment file types from Settings > Security. The rule applies to new uploads and does not delete existing attachments. Blocked upload attempts appear in the audit log."
  },
  {
    "id": "faq-072",
    "category": "Troubleshooting",
    "question": "Why do I see duplicate tasks after import for a small team?",
    "answer": "Duplicate tasks usually happen when the same CSV is imported more than once without using the external ID column. Helios does not merge rows automatically unless an external ID is mapped. Archive or bulk delete the duplicate import batch if needed."
  },
  {
    "id": "faq-073",
    "category": "Billing",
    "question": "Can I cancel my subscription for a small team?",
    "answer": "Owners can cancel from Settings > Billing > Plan. The workspace remains on the paid plan until the end of the current billing period. After that, paid-only features become read-only until the workspace is upgraded again."
  },
  {
    "id": "faq-074",
    "category": "Getting Started",
    "question": "How do I invite teammates for a small team?",
    "answer": "Owners, admins, and permitted members can invite teammates from Settings > Members. Invitations can be sent by email or shared invite link. Pending invites can be revoked before they are accepted."
  },
  {
    "id": "faq-075",
    "category": "Integrations",
    "question": "Can webhooks be retried for a small team?",
    "answer": "Failed webhook deliveries are retried for up to 24 hours with exponential backoff. The delivery log shows response codes and payload IDs. You can manually replay a delivery from the webhook settings page."
  },
  {
    "id": "faq-076",
    "category": "Account Management",
    "question": "How do workspace invites expire for a small team?",
    "answer": "Email invitations expire after seven days. Owners and admins can resend expired invites from Settings > Members. Shared invite links can be manually rotated at any time."
  },
  {
    "id": "faq-077",
    "category": "Permissions & Roles",
    "question": "Can I hide a project from workspace search for a small team?",
    "answer": "Private projects are hidden from users who are not members of the project. They still appear to workspace owners for compliance and recovery. Public projects cannot be hidden from workspace search."
  },
  {
    "id": "faq-078",
    "category": "Notifications",
    "question": "Do mobile push notifications exist for a small team?",
    "answer": "Helios supports mobile push notifications for assignments, mentions, review requests, and due date reminders. Push delivery must be enabled in both Helios and your device settings. Daily digests are email-only."
  },
  {
    "id": "faq-079",
    "category": "Data & Privacy",
    "question": "How are backups handled for a small team?",
    "answer": "Helios takes encrypted backups multiple times per day. Backups are used for disaster recovery and are not browsable by workspace admins. Region-specific workspaces keep backups in the selected region."
  },
  {
    "id": "faq-080",
    "category": "Troubleshooting",
    "question": "What browsers does Helios support for a small team?",
    "answer": "Helios supports the latest two major versions of Chrome, Edge, Firefox, and Safari. Older browsers may load but are not tested. If a supported browser behaves oddly, clear site data and reload before filing a support ticket."
  },
  {
    "id": "faq-081",
    "category": "Billing",
    "question": "How are seat changes prorated after launch?",
    "answer": "When seats are added or removed mid-cycle, Helios prorates the change to the day it happened. Added seats are charged on the next invoice, and removed seats create a credit for unused time. Annual plans show the adjustment as a line item."
  },
  {
    "id": "faq-082",
    "category": "Getting Started",
    "question": "Can I create a project from an existing one after launch?",
    "answer": "Yes. Use Duplicate project from the project menu. Helios copies sections, open tasks, custom fields, and dependencies, but it does not copy private comments by default. You can choose whether assignees and due dates are preserved."
  },
  {
    "id": "faq-083",
    "category": "Integrations",
    "question": "Does Helios have an API after launch?",
    "answer": "Yes. Helios provides a REST API for tasks, projects, users, comments, and custom fields. API tokens are created in Personal settings and inherit the user's permissions. Enterprise workspaces can restrict token creation."
  },
  {
    "id": "faq-084",
    "category": "Account Management",
    "question": "Can I enable single sign-on after launch?",
    "answer": "Business and Enterprise workspaces can enable SAML single sign-on from Settings > Security. Owners should test SSO with optional enforcement before requiring it for everyone. SCIM provisioning is available on Enterprise plans."
  },
  {
    "id": "faq-085",
    "category": "Permissions & Roles",
    "question": "Can I make a project read-only after launch?",
    "answer": "Project admins can set a project to read-only from Project settings > Access. Members can still view tasks and comments, but only project admins can edit content. Read-only mode is useful after a launch or audit period."
  },
  {
    "id": "faq-086",
    "category": "Notifications",
    "question": "Can I route notifications to different Slack channels after launch?",
    "answer": "Yes. Project admins can choose a Slack channel for each project and select which events are posted there. Personal Slack notifications still go to the user's direct messages. Channel routing requires the workspace Slack integration."
  },
  {
    "id": "faq-087",
    "category": "Data & Privacy",
    "question": "Can I delete my personal account after launch?",
    "answer": "You can request account deletion from Personal settings > Privacy. Helios removes personal profile data after verifying that you do not own an active workspace. Your historical comments may remain attributed to a deactivated user for audit integrity."
  },
  {
    "id": "faq-088",
    "category": "Troubleshooting",
    "question": "Why can't I assign a task to someone after launch?",
    "answer": "The person must be an active member or invited guest with access to the project. Deactivated users and users outside the project cannot be assigned new work. If the project is private, add the person to the project first."
  },
  {
    "id": "faq-089",
    "category": "Billing",
    "question": "Can I set a separate billing contact after launch?",
    "answer": "Yes. Owners can add billing contacts in Settings > Billing > Contacts. Billing contacts receive invoices, payment notices, and renewal reminders, but they do not gain access to projects unless they are also workspace members."
  },
  {
    "id": "faq-090",
    "category": "Getting Started",
    "question": "How do task dependencies work after launch?",
    "answer": "A task can be blocked by one or more other tasks. Blocked tasks show a dependency warning until the blocking work is completed. Helios does not automatically change due dates, but timeline views highlight conflicts."
  },
  {
    "id": "faq-091",
    "category": "Integrations",
    "question": "Can I connect Jira to Helios after launch?",
    "answer": "The Jira importer can migrate projects, epics, issues, comments, and basic custom fields into Helios. Continuous two-way Jira sync is not currently supported. Teams that still use Jira can link back to source issues in task descriptions."
  },
  {
    "id": "faq-092",
    "category": "Account Management",
    "question": "How do I change my display name or avatar after launch?",
    "answer": "Open Personal settings > Profile to update your display name, title, timezone, and avatar. Avatar changes may take a few minutes to appear in mentions and activity feeds. SSO-managed profile fields may be locked."
  },
  {
    "id": "faq-093",
    "category": "Permissions & Roles",
    "question": "Who can manage integrations after launch?",
    "answer": "Owners and admins can install or remove workspace integrations. Project admins can configure project-level mappings for integrations that are already installed. Members can connect personal integrations such as calendar sync when allowed."
  },
  {
    "id": "faq-094",
    "category": "Notifications",
    "question": "Why am I not getting due date reminders after launch?",
    "answer": "Due date reminders require a due date, an enabled reminder window, and at least one active delivery channel. Muted projects suppress normal reminders unless you are directly assigned. Check Personal settings > Notifications before contacting support."
  },
  {
    "id": "faq-095",
    "category": "Data & Privacy",
    "question": "Does Helios maintain audit logs after launch?",
    "answer": "Business and Enterprise plans include audit logs for sign-ins, permission changes, exports, integration changes, and workspace settings. Owners can search and export audit logs from Settings > Security. Audit log retention depends on the plan."
  },
  {
    "id": "faq-096",
    "category": "Troubleshooting",
    "question": "Why are GitHub links not updating tasks after launch?",
    "answer": "Confirm that the repository is linked to the project and that the pull request mentions the Helios task ID. Some automation requires the GitHub app to have access to the repository. Reinstalling the GitHub integration can fix missing webhook permissions."
  },
  {
    "id": "faq-097",
    "category": "Billing",
    "question": "Is there a free trial after launch?",
    "answer": "New workspaces start with a 14 day trial of the Business plan. You do not need a credit card to start the trial. If no plan is selected when the trial ends, the workspace moves to the Free plan with Free plan limits."
  },
  {
    "id": "faq-098",
    "category": "Getting Started",
    "question": "Can I use cycles or sprints after launch?",
    "answer": "Yes. Teams can enable cycles from Team settings. Cycles group tasks into fixed planning windows and provide progress, carryover, and scope-change reporting. Projects can use cycles alongside milestones."
  },
  {
    "id": "faq-099",
    "category": "Integrations",
    "question": "Does the Google Drive integration attach files after launch?",
    "answer": "Yes. Users can attach Google Drive files to tasks after connecting their Google account. Helios stores a permission-checked link rather than copying the file contents. Drive permissions still control who can open the document."
  },
  {
    "id": "faq-100",
    "category": "Account Management",
    "question": "Can I restore a deactivated user after launch?",
    "answer": "Owners can reactivate a user from Settings > Members if the account was deactivated rather than deleted. Reactivation restores access to the same teams and projects unless those permissions were changed separately. The user may need to reset their password."
  },
  {
    "id": "faq-101",
    "category": "Permissions & Roles",
    "question": "Can roles be assigned by team after launch?",
    "answer": "Yes. A member can be a project admin in one team and a regular member in another. Workspace owner and admin roles still apply across the entire workspace. Guest access remains limited to invited projects."
  },
  {
    "id": "faq-102",
    "category": "Notifications",
    "question": "Can I subscribe to a task without commenting after launch?",
    "answer": "Yes. Select the bell icon on any task to subscribe. Subscribers receive updates for comments, status changes, and due date changes. You can unsubscribe from the same menu later."
  },
  {
    "id": "faq-103",
    "category": "Data & Privacy",
    "question": "Can attachments be restricted by file type after launch?",
    "answer": "Enterprise owners can restrict attachment file types from Settings > Security. The rule applies to new uploads and does not delete existing attachments. Blocked upload attempts appear in the audit log."
  },
  {
    "id": "faq-104",
    "category": "Troubleshooting",
    "question": "Why do I see duplicate tasks after import after launch?",
    "answer": "Duplicate tasks usually happen when the same CSV is imported more than once without using the external ID column. Helios does not merge rows automatically unless an external ID is mapped. Archive or bulk delete the duplicate import batch if needed."
  },
  {
    "id": "faq-105",
    "category": "Billing",
    "question": "Can I cancel my subscription after launch?",
    "answer": "Owners can cancel from Settings > Billing > Plan. The workspace remains on the paid plan until the end of the current billing period. After that, paid-only features become read-only until the workspace is upgraded again."
  },
  {
    "id": "faq-106",
    "category": "Getting Started",
    "question": "How do I invite teammates after launch?",
    "answer": "Owners, admins, and permitted members can invite teammates from Settings > Members. Invitations can be sent by email or shared invite link. Pending invites can be revoked before they are accepted."
  },
  {
    "id": "faq-107",
    "category": "Integrations",
    "question": "Can webhooks be retried after launch?",
    "answer": "Failed webhook deliveries are retried for up to 24 hours with exponential backoff. The delivery log shows response codes and payload IDs. You can manually replay a delivery from the webhook settings page."
  },
  {
    "id": "faq-108",
    "category": "Account Management",
    "question": "How do workspace invites expire after launch?",
    "answer": "Email invitations expire after seven days. Owners and admins can resend expired invites from Settings > Members. Shared invite links can be manually rotated at any time."
  },
  {
    "id": "faq-109",
    "category": "Permissions & Roles",
    "question": "Can I hide a project from workspace search after launch?",
    "answer": "Private projects are hidden from users who are not members of the project. They still appear to workspace owners for compliance and recovery. Public projects cannot be hidden from workspace search."
  },
  {
    "id": "faq-110",
    "category": "Notifications",
    "question": "Do mobile push notifications exist after launch?",
    "answer": "Helios supports mobile push notifications for assignments, mentions, review requests, and due date reminders. Push delivery must be enabled in both Helios and your device settings. Daily digests are email-only."
  },
  {
    "id": "faq-111",
    "category": "Data & Privacy",
    "question": "How are backups handled after launch?",
    "answer": "Helios takes encrypted backups multiple times per day. Backups are used for disaster recovery and are not browsable by workspace admins. Region-specific workspaces keep backups in the selected region."
  },
  {
    "id": "faq-112",
    "category": "Troubleshooting",
    "question": "What browsers does Helios support after launch?",
    "answer": "Helios supports the latest two major versions of Chrome, Edge, Firefox, and Safari. Older browsers may load but are not tested. If a supported browser behaves oddly, clear site data and reload before filing a support ticket."
  },
  {
    "id": "faq-113",
    "category": "Billing",
    "question": "How are seat changes prorated during onboarding?",
    "answer": "When seats are added or removed mid-cycle, Helios prorates the change to the day it happened. Added seats are charged on the next invoice, and removed seats create a credit for unused time. Annual plans show the adjustment as a line item."
  },
  {
    "id": "faq-114",
    "category": "Getting Started",
    "question": "Can I create a project from an existing one during onboarding?",
    "answer": "Yes. Use Duplicate project from the project menu. Helios copies sections, open tasks, custom fields, and dependencies, but it does not copy private comments by default. You can choose whether assignees and due dates are preserved."
  },
  {
    "id": "faq-115",
    "category": "Integrations",
    "question": "Does Helios have an API during onboarding?",
    "answer": "Yes. Helios provides a REST API for tasks, projects, users, comments, and custom fields. API tokens are created in Personal settings and inherit the user's permissions. Enterprise workspaces can restrict token creation."
  },
  {
    "id": "faq-116",
    "category": "Account Management",
    "question": "Can I enable single sign-on during onboarding?",
    "answer": "Business and Enterprise workspaces can enable SAML single sign-on from Settings > Security. Owners should test SSO with optional enforcement before requiring it for everyone. SCIM provisioning is available on Enterprise plans."
  },
  {
    "id": "faq-117",
    "category": "Permissions & Roles",
    "question": "Can I make a project read-only during onboarding?",
    "answer": "Project admins can set a project to read-only from Project settings > Access. Members can still view tasks and comments, but only project admins can edit content. Read-only mode is useful after a launch or audit period."
  },
  {
    "id": "faq-118",
    "category": "Notifications",
    "question": "Can I route notifications to different Slack channels during onboarding?",
    "answer": "Yes. Project admins can choose a Slack channel for each project and select which events are posted there. Personal Slack notifications still go to the user's direct messages. Channel routing requires the workspace Slack integration."
  },
  {
    "id": "faq-119",
    "category": "Data & Privacy",
    "question": "Can I delete my personal account during onboarding?",
    "answer": "You can request account deletion from Personal settings > Privacy. Helios removes personal profile data after verifying that you do not own an active workspace. Your historical comments may remain attributed to a deactivated user for audit integrity."
  },
  {
    "id": "faq-120",
    "category": "Troubleshooting",
    "question": "Why can't I assign a task to someone during onboarding?",
    "answer": "The person must be an active member or invited guest with access to the project. Deactivated users and users outside the project cannot be assigned new work. If the project is private, add the person to the project first."
  },
  {
    "id": "faq-121",
    "category": "Billing",
    "question": "Can I set a separate billing contact during onboarding?",
    "answer": "Yes. Owners can add billing contacts in Settings > Billing > Contacts. Billing contacts receive invoices, payment notices, and renewal reminders, but they do not gain access to projects unless they are also workspace members."
  },
  {
    "id": "faq-122",
    "category": "Getting Started",
    "question": "How do task dependencies work during onboarding?",
    "answer": "A task can be blocked by one or more other tasks. Blocked tasks show a dependency warning until the blocking work is completed. Helios does not automatically change due dates, but timeline views highlight conflicts."
  },
  {
    "id": "faq-123",
    "category": "Integrations",
    "question": "Can I connect Jira to Helios during onboarding?",
    "answer": "The Jira importer can migrate projects, epics, issues, comments, and basic custom fields into Helios. Continuous two-way Jira sync is not currently supported. Teams that still use Jira can link back to source issues in task descriptions."
  },
  {
    "id": "faq-124",
    "category": "Account Management",
    "question": "How do I change my display name or avatar during onboarding?",
    "answer": "Open Personal settings > Profile to update your display name, title, timezone, and avatar. Avatar changes may take a few minutes to appear in mentions and activity feeds. SSO-managed profile fields may be locked."
  },
  {
    "id": "faq-125",
    "category": "Permissions & Roles",
    "question": "Who can manage integrations during onboarding?",
    "answer": "Owners and admins can install or remove workspace integrations. Project admins can configure project-level mappings for integrations that are already installed. Members can connect personal integrations such as calendar sync when allowed."
  },
  {
    "id": "faq-126",
    "category": "Notifications",
    "question": "Why am I not getting due date reminders during onboarding?",
    "answer": "Due date reminders require a due date, an enabled reminder window, and at least one active delivery channel. Muted projects suppress normal reminders unless you are directly assigned. Check Personal settings > Notifications before contacting support."
  },
  {
    "id": "faq-127",
    "category": "Data & Privacy",
    "question": "Does Helios maintain audit logs during onboarding?",
    "answer": "Business and Enterprise plans include audit logs for sign-ins, permission changes, exports, integration changes, and workspace settings. Owners can search and export audit logs from Settings > Security. Audit log retention depends on the plan."
  },
  {
    "id": "faq-128",
    "category": "Troubleshooting",
    "question": "Why are GitHub links not updating tasks during onboarding?",
    "answer": "Confirm that the repository is linked to the project and that the pull request mentions the Helios task ID. Some automation requires the GitHub app to have access to the repository. Reinstalling the GitHub integration can fix missing webhook permissions."
  },
  {
    "id": "faq-129",
    "category": "Billing",
    "question": "Is there a free trial during onboarding?",
    "answer": "New workspaces start with a 14 day trial of the Business plan. You do not need a credit card to start the trial. If no plan is selected when the trial ends, the workspace moves to the Free plan with Free plan limits."
  },
  {
    "id": "faq-130",
    "category": "Getting Started",
    "question": "Can I use cycles or sprints during onboarding?",
    "answer": "Yes. Teams can enable cycles from Team settings. Cycles group tasks into fixed planning windows and provide progress, carryover, and scope-change reporting. Projects can use cycles alongside milestones."
  },
  {
    "id": "faq-131",
    "category": "Integrations",
    "question": "Does the Google Drive integration attach files during onboarding?",
    "answer": "Yes. Users can attach Google Drive files to tasks after connecting their Google account. Helios stores a permission-checked link rather than copying the file contents. Drive permissions still control who can open the document."
  },
  {
    "id": "faq-132",
    "category": "Account Management",
    "question": "Can I restore a deactivated user during onboarding?",
    "answer": "Owners can reactivate a user from Settings > Members if the account was deactivated rather than deleted. Reactivation restores access to the same teams and projects unless those permissions were changed separately. The user may need to reset their password."
  },
  {
    "id": "faq-133",
    "category": "Permissions & Roles",
    "question": "Can roles be assigned by team during onboarding?",
    "answer": "Yes. A member can be a project admin in one team and a regular member in another. Workspace owner and admin roles still apply across the entire workspace. Guest access remains limited to invited projects."
  },
  {
    "id": "faq-134",
    "category": "Notifications",
    "question": "Can I subscribe to a task without commenting during onboarding?",
    "answer": "Yes. Select the bell icon on any task to subscribe. Subscribers receive updates for comments, status changes, and due date changes. You can unsubscribe from the same menu later."
  },
  {
    "id": "faq-135",
    "category": "Data & Privacy",
    "question": "Can attachments be restricted by file type during onboarding?",
    "answer": "Enterprise owners can restrict attachment file types from Settings > Security. The rule applies to new uploads and does not delete existing attachments. Blocked upload attempts appear in the audit log."
  },
  {
    "id": "faq-136",
    "category": "Troubleshooting",
    "question": "Why do I see duplicate tasks after import during onboarding?",
    "answer": "Duplicate tasks usually happen when the same CSV is imported more than once without using the external ID column. Helios does not merge rows automatically unless an external ID is mapped. Archive or bulk delete the duplicate import batch if needed."
  },
  {
    "id": "faq-137",
    "category": "Billing",
    "question": "Can I cancel my subscription during onboarding?",
    "answer": "Owners can cancel from Settings > Billing > Plan. The workspace remains on the paid plan until the end of the current billing period. After that, paid-only features become read-only until the workspace is upgraded again."
  },
  {
    "id": "faq-138",
    "category": "Getting Started",
    "question": "How do I invite teammates during onboarding?",
    "answer": "Owners, admins, and permitted members can invite teammates from Settings > Members. Invitations can be sent by email or shared invite link. Pending invites can be revoked before they are accepted."
  },
  {
    "id": "faq-139",
    "category": "Integrations",
    "question": "Can webhooks be retried during onboarding?",
    "answer": "Failed webhook deliveries are retried for up to 24 hours with exponential backoff. The delivery log shows response codes and payload IDs. You can manually replay a delivery from the webhook settings page."
  },
  {
    "id": "faq-140",
    "category": "Account Management",
    "question": "How do workspace invites expire during onboarding?",
    "answer": "Email invitations expire after seven days. Owners and admins can resend expired invites from Settings > Members. Shared invite links can be manually rotated at any time."
  },
  {
    "id": "faq-141",
    "category": "Permissions & Roles",
    "question": "Can I hide a project from workspace search during onboarding?",
    "answer": "Private projects are hidden from users who are not members of the project. They still appear to workspace owners for compliance and recovery. Public projects cannot be hidden from workspace search."
  },
  {
    "id": "faq-142",
    "category": "Notifications",
    "question": "Do mobile push notifications exist during onboarding?",
    "answer": "Helios supports mobile push notifications for assignments, mentions, review requests, and due date reminders. Push delivery must be enabled in both Helios and your device settings. Daily digests are email-only."
  },
  {
    "id": "faq-143",
    "category": "Data & Privacy",
    "question": "How are backups handled during onboarding?",
    "answer": "Helios takes encrypted backups multiple times per day. Backups are used for disaster recovery and are not browsable by workspace admins. Region-specific workspaces keep backups in the selected region."
  },
  {
    "id": "faq-144",
    "category": "Troubleshooting",
    "question": "What browsers does Helios support during onboarding?",
    "answer": "Helios supports the latest two major versions of Chrome, Edge, Firefox, and Safari. Older browsers may load but are not tested. If a supported browser behaves oddly, clear site data and reload before filing a support ticket."
  },
  {
    "id": "faq-145",
    "category": "Billing",
    "question": "How are seat changes prorated for contractors?",
    "answer": "When seats are added or removed mid-cycle, Helios prorates the change to the day it happened. Added seats are charged on the next invoice, and removed seats create a credit for unused time. Annual plans show the adjustment as a line item."
  },
  {
    "id": "faq-146",
    "category": "Getting Started",
    "question": "Can I create a project from an existing one for contractors?",
    "answer": "Yes. Use Duplicate project from the project menu. Helios copies sections, open tasks, custom fields, and dependencies, but it does not copy private comments by default. You can choose whether assignees and due dates are preserved."
  },
  {
    "id": "faq-147",
    "category": "Integrations",
    "question": "Does Helios have an API for contractors?",
    "answer": "Yes. Helios provides a REST API for tasks, projects, users, comments, and custom fields. API tokens are created in Personal settings and inherit the user's permissions. Enterprise workspaces can restrict token creation."
  },
  {
    "id": "faq-148",
    "category": "Account Management",
    "question": "Can I enable single sign-on for contractors?",
    "answer": "Business and Enterprise workspaces can enable SAML single sign-on from Settings > Security. Owners should test SSO with optional enforcement before requiring it for everyone. SCIM provisioning is available on Enterprise plans."
  },
  {
    "id": "faq-149",
    "category": "Permissions & Roles",
    "question": "Can I make a project read-only for contractors?",
    "answer": "Project admins can set a project to read-only from Project settings > Access. Members can still view tasks and comments, but only project admins can edit content. Read-only mode is useful after a launch or audit period."
  },
  {
    "id": "faq-150",
    "category": "Notifications",
    "question": "Can I route notifications to different Slack channels for contractors?",
    "answer": "Yes. Project admins can choose a Slack channel for each project and select which events are posted there. Personal Slack notifications still go to the user's direct messages. Channel routing requires the workspace Slack integration."
  },
  {
    "id": "faq-151",
    "category": "Data & Privacy",
    "question": "Can I delete my personal account for contractors?",
    "answer": "You can request account deletion from Personal settings > Privacy. Helios removes personal profile data after verifying that you do not own an active workspace. Your historical comments may remain attributed to a deactivated user for audit integrity."
  },
  {
    "id": "faq-152",
    "category": "Troubleshooting",
    "question": "Why can't I assign a task to someone for contractors?",
    "answer": "The person must be an active member or invited guest with access to the project. Deactivated users and users outside the project cannot be assigned new work. If the project is private, add the person to the project first."
  },
  {
    "id": "faq-153",
    "category": "Billing",
    "question": "Can I set a separate billing contact for contractors?",
    "answer": "Yes. Owners can add billing contacts in Settings > Billing > Contacts. Billing contacts receive invoices, payment notices, and renewal reminders, but they do not gain access to projects unless they are also workspace members."
  },
  {
    "id": "faq-154",
    "category": "Getting Started",
    "question": "How do task dependencies work for contractors?",
    "answer": "A task can be blocked by one or more other tasks. Blocked tasks show a dependency warning until the blocking work is completed. Helios does not automatically change due dates, but timeline views highlight conflicts."
  },
  {
    "id": "faq-155",
    "category": "Integrations",
    "question": "Can I connect Jira to Helios for contractors?",
    "answer": "The Jira importer can migrate projects, epics, issues, comments, and basic custom fields into Helios. Continuous two-way Jira sync is not currently supported. Teams that still use Jira can link back to source issues in task descriptions."
  },
  {
    "id": "faq-156",
    "category": "Account Management",
    "question": "How do I change my display name or avatar for contractors?",
    "answer": "Open Personal settings > Profile to update your display name, title, timezone, and avatar. Avatar changes may take a few minutes to appear in mentions and activity feeds. SSO-managed profile fields may be locked."
  },
  {
    "id": "faq-157",
    "category": "Permissions & Roles",
    "question": "Who can manage integrations for contractors?",
    "answer": "Owners and admins can install or remove workspace integrations. Project admins can configure project-level mappings for integrations that are already installed. Members can connect personal integrations such as calendar sync when allowed."
  },
  {
    "id": "faq-158",
    "category": "Notifications",
    "question": "Why am I not getting due date reminders for contractors?",
    "answer": "Due date reminders require a due date, an enabled reminder window, and at least one active delivery channel. Muted projects suppress normal reminders unless you are directly assigned. Check Personal settings > Notifications before contacting support."
  },
  {
    "id": "faq-159",
    "category": "Data & Privacy",
    "question": "Does Helios maintain audit logs for contractors?",
    "answer": "Business and Enterprise plans include audit logs for sign-ins, permission changes, exports, integration changes, and workspace settings. Owners can search and export audit logs from Settings > Security. Audit log retention depends on the plan."
  },
  {
    "id": "faq-160",
    "category": "Troubleshooting",
    "question": "Why are GitHub links not updating tasks for contractors?",
    "answer": "Confirm that the repository is linked to the project and that the pull request mentions the Helios task ID. Some automation requires the GitHub app to have access to the repository. Reinstalling the GitHub integration can fix missing webhook permissions."
  },
  {
    "id": "faq-161",
    "category": "Billing",
    "question": "Is there a free trial for contractors?",
    "answer": "New workspaces start with a 14 day trial of the Business plan. You do not need a credit card to start the trial. If no plan is selected when the trial ends, the workspace moves to the Free plan with Free plan limits."
  },
  {
    "id": "faq-162",
    "category": "Getting Started",
    "question": "Can I use cycles or sprints for contractors?",
    "answer": "Yes. Teams can enable cycles from Team settings. Cycles group tasks into fixed planning windows and provide progress, carryover, and scope-change reporting. Projects can use cycles alongside milestones."
  },
  {
    "id": "faq-163",
    "category": "Integrations",
    "question": "Does the Google Drive integration attach files for contractors?",
    "answer": "Yes. Users can attach Google Drive files to tasks after connecting their Google account. Helios stores a permission-checked link rather than copying the file contents. Drive permissions still control who can open the document."
  },
  {
    "id": "faq-164",
    "category": "Account Management",
    "question": "Can I restore a deactivated user for contractors?",
    "answer": "Owners can reactivate a user from Settings > Members if the account was deactivated rather than deleted. Reactivation restores access to the same teams and projects unless those permissions were changed separately. The user may need to reset their password."
  },
  {
    "id": "faq-165",
    "category": "Permissions & Roles",
    "question": "Can roles be assigned by team for contractors?",
    "answer": "Yes. A member can be a project admin in one team and a regular member in another. Workspace owner and admin roles still apply across the entire workspace. Guest access remains limited to invited projects."
  },
  {
    "id": "faq-166",
    "category": "Notifications",
    "question": "Can I subscribe to a task without commenting for contractors?",
    "answer": "Yes. Select the bell icon on any task to subscribe. Subscribers receive updates for comments, status changes, and due date changes. You can unsubscribe from the same menu later."
  },
  {
    "id": "faq-167",
    "category": "Data & Privacy",
    "question": "Can attachments be restricted by file type for contractors?",
    "answer": "Enterprise owners can restrict attachment file types from Settings > Security. The rule applies to new uploads and does not delete existing attachments. Blocked upload attempts appear in the audit log."
  },
  {
    "id": "faq-168",
    "category": "Troubleshooting",
    "question": "Why do I see duplicate tasks after import for contractors?",
    "answer": "Duplicate tasks usually happen when the same CSV is imported more than once without using the external ID column. Helios does not merge rows automatically unless an external ID is mapped. Archive or bulk delete the duplicate import batch if needed."
  },
  {
    "id": "faq-169",
    "category": "Billing",
    "question": "Can I cancel my subscription for contractors?",
    "answer": "Owners can cancel from Settings > Billing > Plan. The workspace remains on the paid plan until the end of the current billing period. After that, paid-only features become read-only until the workspace is upgraded again."
  },
  {
    "id": "faq-170",
    "category": "Getting Started",
    "question": "How do I invite teammates for contractors?",
    "answer": "Owners, admins, and permitted members can invite teammates from Settings > Members. Invitations can be sent by email or shared invite link. Pending invites can be revoked before they are accepted."
  },
  {
    "id": "faq-171",
    "category": "Integrations",
    "question": "Can webhooks be retried for contractors?",
    "answer": "Failed webhook deliveries are retried for up to 24 hours with exponential backoff. The delivery log shows response codes and payload IDs. You can manually replay a delivery from the webhook settings page."
  },
  {
    "id": "faq-172",
    "category": "Account Management",
    "question": "How do workspace invites expire for contractors?",
    "answer": "Email invitations expire after seven days. Owners and admins can resend expired invites from Settings > Members. Shared invite links can be manually rotated at any time."
  },
  {
    "id": "faq-173",
    "category": "Permissions & Roles",
    "question": "Can I hide a project from workspace search for contractors?",
    "answer": "Private projects are hidden from users who are not members of the project. They still appear to workspace owners for compliance and recovery. Public projects cannot be hidden from workspace search."
  },
  {
    "id": "faq-174",
    "category": "Notifications",
    "question": "Do mobile push notifications exist for contractors?",
    "answer": "Helios supports mobile push notifications for assignments, mentions, review requests, and due date reminders. Push delivery must be enabled in both Helios and your device settings. Daily digests are email-only."
  },
  {
    "id": "faq-175",
    "category": "Data & Privacy",
    "question": "How are backups handled for contractors?",
    "answer": "Helios takes encrypted backups multiple times per day. Backups are used for disaster recovery and are not browsable by workspace admins. Region-specific workspaces keep backups in the selected region."
  },
  {
    "id": "faq-176",
    "category": "Troubleshooting",
    "question": "What browsers does Helios support for contractors?",
    "answer": "Helios supports the latest two major versions of Chrome, Edge, Firefox, and Safari. Older browsers may load but are not tested. If a supported browser behaves oddly, clear site data and reload before filing a support ticket."
  },
  {
    "id": "faq-177",
    "category": "Billing",
    "question": "How are seat changes prorated on the Business plan?",
    "answer": "When seats are added or removed mid-cycle, Helios prorates the change to the day it happened. Added seats are charged on the next invoice, and removed seats create a credit for unused time. Annual plans show the adjustment as a line item."
  },
  {
    "id": "faq-178",
    "category": "Getting Started",
    "question": "Can I create a project from an existing one on the Business plan?",
    "answer": "Yes. Use Duplicate project from the project menu. Helios copies sections, open tasks, custom fields, and dependencies, but it does not copy private comments by default. You can choose whether assignees and due dates are preserved."
  },
  {
    "id": "faq-179",
    "category": "Integrations",
    "question": "Does Helios have an API on the Business plan?",
    "answer": "Yes. Helios provides a REST API for tasks, projects, users, comments, and custom fields. API tokens are created in Personal settings and inherit the user's permissions. Enterprise workspaces can restrict token creation."
  },
  {
    "id": "faq-180",
    "category": "Account Management",
    "question": "Can I enable single sign-on on the Business plan?",
    "answer": "Business and Enterprise workspaces can enable SAML single sign-on from Settings > Security. Owners should test SSO with optional enforcement before requiring it for everyone. SCIM provisioning is available on Enterprise plans."
  },
  {
    "id": "faq-181",
    "category": "Permissions & Roles",
    "question": "Can I make a project read-only on the Business plan?",
    "answer": "Project admins can set a project to read-only from Project settings > Access. Members can still view tasks and comments, but only project admins can edit content. Read-only mode is useful after a launch or audit period."
  },
  {
    "id": "faq-182",
    "category": "Notifications",
    "question": "Can I route notifications to different Slack channels on the Business plan?",
    "answer": "Yes. Project admins can choose a Slack channel for each project and select which events are posted there. Personal Slack notifications still go to the user's direct messages. Channel routing requires the workspace Slack integration."
  },
  {
    "id": "faq-183",
    "category": "Data & Privacy",
    "question": "Can I delete my personal account on the Business plan?",
    "answer": "You can request account deletion from Personal settings > Privacy. Helios removes personal profile data after verifying that you do not own an active workspace. Your historical comments may remain attributed to a deactivated user for audit integrity."
  },
  {
    "id": "faq-184",
    "category": "Troubleshooting",
    "question": "Why can't I assign a task to someone on the Business plan?",
    "answer": "The person must be an active member or invited guest with access to the project. Deactivated users and users outside the project cannot be assigned new work. If the project is private, add the person to the project first."
  },
  {
    "id": "faq-185",
    "category": "Billing",
    "question": "Can I set a separate billing contact on the Business plan?",
    "answer": "Yes. Owners can add billing contacts in Settings > Billing > Contacts. Billing contacts receive invoices, payment notices, and renewal reminders, but they do not gain access to projects unless they are also workspace members."
  },
  {
    "id": "faq-186",
    "category": "Getting Started",
    "question": "How do task dependencies work on the Business plan?",
    "answer": "A task can be blocked by one or more other tasks. Blocked tasks show a dependency warning until the blocking work is completed. Helios does not automatically change due dates, but timeline views highlight conflicts."
  },
  {
    "id": "faq-187",
    "category": "Integrations",
    "question": "Can I connect Jira to Helios on the Business plan?",
    "answer": "The Jira importer can migrate projects, epics, issues, comments, and basic custom fields into Helios. Continuous two-way Jira sync is not currently supported. Teams that still use Jira can link back to source issues in task descriptions."
  },
  {
    "id": "faq-188",
    "category": "Account Management",
    "question": "How do I change my display name or avatar on the Business plan?",
    "answer": "Open Personal settings > Profile to update your display name, title, timezone, and avatar. Avatar changes may take a few minutes to appear in mentions and activity feeds. SSO-managed profile fields may be locked."
  },
  {
    "id": "faq-189",
    "category": "Permissions & Roles",
    "question": "Who can manage integrations on the Business plan?",
    "answer": "Owners and admins can install or remove workspace integrations. Project admins can configure project-level mappings for integrations that are already installed. Members can connect personal integrations such as calendar sync when allowed."
  },
  {
    "id": "faq-190",
    "category": "Notifications",
    "question": "Why am I not getting due date reminders on the Business plan?",
    "answer": "Due date reminders require a due date, an enabled reminder window, and at least one active delivery channel. Muted projects suppress normal reminders unless you are directly assigned. Check Personal settings > Notifications before contacting support."
  },
  {
    "id": "faq-191",
    "category": "Data & Privacy",
    "question": "Does Helios maintain audit logs on the Business plan?",
    "answer": "Business and Enterprise plans include audit logs for sign-ins, permission changes, exports, integration changes, and workspace settings. Owners can search and export audit logs from Settings > Security. Audit log retention depends on the plan."
  },
  {
    "id": "faq-192",
    "category": "Troubleshooting",
    "question": "Why are GitHub links not updating tasks on the Business plan?",
    "answer": "Confirm that the repository is linked to the project and that the pull request mentions the Helios task ID. Some automation requires the GitHub app to have access to the repository. Reinstalling the GitHub integration can fix missing webhook permissions."
  },
  {
    "id": "faq-193",
    "category": "Billing",
    "question": "Is there a free trial on the Business plan?",
    "answer": "New workspaces start with a 14 day trial of the Business plan. You do not need a credit card to start the trial. If no plan is selected when the trial ends, the workspace moves to the Free plan with Free plan limits."
  },
  {
    "id": "faq-194",
    "category": "Getting Started",
    "question": "Can I use cycles or sprints on the Business plan?",
    "answer": "Yes. Teams can enable cycles from Team settings. Cycles group tasks into fixed planning windows and provide progress, carryover, and scope-change reporting. Projects can use cycles alongside milestones."
  },
  {
    "id": "faq-195",
    "category": "Integrations",
    "question": "Does the Google Drive integration attach files on the Business plan?",
    "answer": "Yes. Users can attach Google Drive files to tasks after connecting their Google account. Helios stores a permission-checked link rather than copying the file contents. Drive permissions still control who can open the document."
  },
  {
    "id": "faq-196",
    "category": "Account Management",
    "question": "Can I restore a deactivated user on the Business plan?",
    "answer": "Owners can reactivate a user from Settings > Members if the account was deactivated rather than deleted. Reactivation restores access to the same teams and projects unless those permissions were changed separately. The user may need to reset their password."
  },
  {
    "id": "faq-197",
    "category": "Permissions & Roles",
    "question": "Can roles be assigned by team on the Business plan?",
    "answer": "Yes. A member can be a project admin in one team and a regular member in another. Workspace owner and admin roles still apply across the entire workspace. Guest access remains limited to invited projects."
  },
  {
    "id": "faq-198",
    "category": "Notifications",
    "question": "Can I subscribe to a task without commenting on the Business plan?",
    "answer": "Yes. Select the bell icon on any task to subscribe. Subscribers receive updates for comments, status changes, and due date changes. You can unsubscribe from the same menu later."
  },
  {
    "id": "faq-199",
    "category": "Data & Privacy",
    "question": "Can attachments be restricted by file type on the Business plan?",
    "answer": "Enterprise owners can restrict attachment file types from Settings > Security. The rule applies to new uploads and does not delete existing attachments. Blocked upload attempts appear in the audit log."
  },
  {
    "id": "faq-200",
    "category": "Troubleshooting",
    "question": "Why do I see duplicate tasks after import on the Business plan?",
    "answer": "Duplicate tasks usually happen when the same CSV is imported more than once without using the external ID column. Helios does not merge rows automatically unless an external ID is mapped. Archive or bulk delete the duplicate import batch if needed."
  }
]"""

# ── TF-IDF Retriever ─────────────────────────────────────────────────────────
def _tok(t): return re.findall(r"[a-z0-9]+", t.lower())

def build_index(faqs):
    corpus = [f"{f['question']} {f['answer']} {f['category']}" for f in faqs]
    tok = [_tok(d) for d in corpus]
    N = len(corpus)
    df = {}
    for ts in tok:
        for t in set(ts): df[t] = df.get(t,0)+1
    idf = {t: math.log((N+1)/(v+1))+1 for t,v in df.items()}
    vecs = []
    for ts in tok:
        c = {}
        for t in ts: c[t]=c.get(t,0)+1
        n = len(ts) or 1
        vecs.append({t:(v/n)*idf.get(t,1) for t,v in c.items()})
    return vecs, idf

def cosine(a, b):
    dot = sum(a.get(t,0)*b.get(t,0) for t in b)
    return dot / ((math.sqrt(sum(v*v for v in a.values())) or 1e-9) *
                  (math.sqrt(sum(v*v for v in b.values())) or 1e-9))

def retrieve(query, faqs, vecs, idf, k=TOP_K):
    c = {}
    for t in _tok(query): c[t]=c.get(t,0)+1
    n = len(c) or 1
    qv = {t:(v/n)*idf.get(t,1) for t,v in c.items()}
    if not qv: return []
    scored = sorted(enumerate(faqs), key=lambda x: cosine(vecs[x[0]], qv), reverse=True)
    return [f for _,f in scored[:k]]

# ── LLM call ─────────────────────────────────────────────────────────────────
SYSTEM = ("You are a helpful Helios customer support agent. "
          "Answer using ONLY the FAQ context provided. Be concise (2-4 sentences). "
          "If the context is insufficient, say so. "
          "End with cited FAQ IDs, e.g. (Sources: faq-001, faq-002).")

def generate(question, hits):
    if not hits:
        return ("No relevant FAQ entries found. Please contact Helios support.", [])
    ctx = "\n\n".join(f"[{f['id']}] ({f['category']})\nQ: {f['question']}\nA: {f['answer']}" for f in hits)
    if not ANTHROPIC_API_KEY:
        b = hits[0]
        return (f"{b['answer']} (Sources: {b['id']})", [b["id"]])
    body = json.dumps({
        "model": MODEL, "max_tokens": MAX_TOKENS,
        "system": SYSTEM,
        "messages": [{"role":"user","content":f"FAQ context:\n{ctx}\n\nCustomer question: {question}"}]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key":ANTHROPIC_API_KEY,"anthropic-version":"2023-06-01",
                 "content-type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        ans = json.loads(r.read())["content"][0]["text"].strip()
    cited = list(dict.fromkeys(re.findall(r"faq-\d+", ans.lower())))
    return ans, cited or [f["id"] for f in hits]

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    faqs  = json.loads(DATASET_JSON)
    vecs, idf = build_index(faqs)
    print(f"Index ready ({len(faqs)} entries).", flush=True)

    with open(TEST_INPUTS_PATH) as f:
        tests = json.load(f)
    print(f"Processing {len(tests)} questions...", flush=True)

    results = []
    for item in tests:
        q = item["input"].get("question", item["input"].get("query",""))
        hits = retrieve(q, faqs, vecs, idf)
        ans, sources = generate(q, hits)
        results.append({"id": item["id"], "output": {"answer": ans, "sources": sources}})
        print(f"  [{item['id']}] done", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(RESULTS_PATH)), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {len(results)} results → {RESULTS_PATH}", flush=True)

if __name__ == "__main__":
    main()
