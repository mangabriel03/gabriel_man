import { useEffect, useState } from "react";

import {
  createAdminUser,
  fetchAdminUsers,
  type AdminUserCreateRequest,
  type AdminUserListItem,
} from "../../api/users";
import { ApiError, ApiValidationError } from "../../api/client";
import styles from "./UserListPage.module.css";


const ROLE_LABELS: Record<string, string> = {
  SYSTEM_ADMIN: "System Admin",
  COLLEAGUE: "Colleague",
  PASSENGER: "Passenger",
};


export function UserListPage() {
  const [formValues, setFormValues] = useState<AdminUserCreateRequest>({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [users, setUsers] = useState<AdminUserListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function setFieldValue(field: keyof AdminUserCreateRequest, value: string) {
    setFormValues((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => {
      if (!(field in current)) {
        return current;
      }

      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  function getFieldError(field: keyof AdminUserCreateRequest): string | null {
    return fieldErrors[field] ?? null;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFieldErrors({});
    setSuccess(null);
    setError(null);

    try {
      const createdUser = await createAdminUser(formValues);
      setUsers((current) => {
        const next = [...current, createdUser];
        return next.sort(
          (left, right) => left.name.localeCompare(right.name) || left.email.localeCompare(right.email),
        );
      });
      setFormValues({
        first_name: "",
        last_name: "",
        email: "",
        password: "",
      });
      setSuccess(createdUser.detail);
    } catch (err) {
      if (err instanceof ApiValidationError) {
        const nextErrors: Record<string, string> = {};
        for (const [field, value] of Object.entries(err.fieldErrors)) {
          if (Array.isArray(value) && typeof value[0] === "string") {
            nextErrors[field] = value[0];
          }
        }
        setFieldErrors(nextErrors);
      } else if (err instanceof ApiError && err.status === 403) {
        setError("You need system admin access to create users.");
      } else {
        setError("Could not create the account right now.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function loadUsers() {
      try {
        const response = await fetchAdminUsers();
        if (!active) {
          return;
        }
        setUsers(response);
      } catch (err) {
        if (!active) {
          return;
        }
        if (err instanceof ApiError && err.status === 403) {
          setError("You need system admin access to view users.");
        } else {
          setError("Could not load users right now.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadUsers();

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <section className={styles.card} aria-labelledby="user-list-title">
          <div className={styles.header}>
            <div>
              <p className={styles.eyebrow}>System administration</p>
              <h1 id="user-list-title" className={styles.title}>User directory</h1>
              <p className={styles.intro}>
                Review every account in the system, including role assignment and linked case volume.
              </p>
            </div>
            <div className={styles.summary}>
              <span className={styles.summaryLabel}>Users</span>
              <strong className={styles.summaryValue}>{users.length}</strong>
            </div>
          </div>

          <section id="create-user" className={styles.formCard} aria-labelledby="create-user-title">
            <div className={styles.formHeader}>
              <h2 id="create-user-title" className={styles.sectionTitle}>Create colleague account</h2>
              <p className={styles.sectionIntro}>
                Add a colleague with a temporary password that must be changed on first sign-in.
              </p>
            </div>

            {success && <div className={`${styles.banner} ${styles.bannerSuccess}`}>{success}</div>}

            <form className={styles.form} onSubmit={handleSubmit}>
              <div className={styles.formGrid}>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="create-user-first-name">First name</label>
                  <input
                    id="create-user-first-name"
                    className={styles.input}
                    type="text"
                    value={formValues.first_name}
                    onChange={(event) => setFieldValue("first_name", event.target.value)}
                    aria-invalid={getFieldError("first_name") ? "true" : "false"}
                  />
                  {getFieldError("first_name") && <p className={styles.fieldError}>{getFieldError("first_name")}</p>}
                </div>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="create-user-last-name">Last name</label>
                  <input
                    id="create-user-last-name"
                    className={styles.input}
                    type="text"
                    value={formValues.last_name}
                    onChange={(event) => setFieldValue("last_name", event.target.value)}
                    aria-invalid={getFieldError("last_name") ? "true" : "false"}
                  />
                  {getFieldError("last_name") && <p className={styles.fieldError}>{getFieldError("last_name")}</p>}
                </div>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="create-user-email">E-mail address</label>
                  <input
                    id="create-user-email"
                    className={styles.input}
                    type="email"
                    autoComplete="email"
                    value={formValues.email}
                    onChange={(event) => setFieldValue("email", event.target.value)}
                    aria-invalid={getFieldError("email") ? "true" : "false"}
                  />
                  {getFieldError("email") && <p className={styles.fieldError}>{getFieldError("email")}</p>}
                </div>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="create-user-password">Initial password</label>
                  <input
                    id="create-user-password"
                    className={styles.input}
                    type="password"
                    autoComplete="new-password"
                    value={formValues.password}
                    onChange={(event) => setFieldValue("password", event.target.value)}
                    aria-invalid={getFieldError("password") ? "true" : "false"}
                  />
                  {getFieldError("password") && <p className={styles.fieldError}>{getFieldError("password")}</p>}
                </div>
              </div>
              <div className={styles.formActions}>
                <button type="submit" className={styles.primaryButton} disabled={submitting}>
                  {submitting ? "Creating account..." : "Create account"}
                </button>
              </div>
            </form>
          </section>

          {loading && <div className={styles.banner}>Loading users...</div>}
          {error && <div className={`${styles.banner} ${styles.bannerError}`}>{error}</div>}

          {!loading && !error && (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">E-Mail</th>
                    <th scope="col">Role</th>
                    <th scope="col">Assigned cases</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td>{user.name || "No name provided"}</td>
                      <td>{user.email}</td>
                      <td>
                        <span className={styles.roleBadge}>
                          {ROLE_LABELS[user.role] ?? user.role}
                        </span>
                      </td>
                      <td>{user.assigned_case_count}</td>
                      <td>
                        <div className={styles.actions}>
                          <button type="button" className={styles.secondaryButton}>
                            Edit
                          </button>
                          <button type="button" className={styles.dangerButton}>
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}