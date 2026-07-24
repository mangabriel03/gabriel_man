import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { deleteAdminCase, fetchAdminCases, type AdminCaseListItem } from "../../api/adminCases";
import { ApiError } from "../../api/client";
import styles from "./AdminCaseListPage.module.css";


export function AdminCaseListPage() {
  const [cases, setCases] = useState<AdminCaseListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [deletingCaseId, setDeletingCaseId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadCases() {
      try {
        const response = await fetchAdminCases();
        if (!active) {
          return;
        }
        setCases(response);
      } catch (err) {
        if (!active) {
          return;
        }
        if (err instanceof ApiError && err.status === 403) {
          setError("You need system admin access to view cases.");
        } else {
          setError("Could not load cases right now.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadCases();

    return () => {
      active = false;
    };
  }, []);

  async function handleDelete(caseItem: AdminCaseListItem) {
    const confirmed = window.confirm(
      `Delete case ${caseItem.id}? This permanently removes its flight segments and uploaded documents.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingCaseId(caseItem.id);
    setSuccess(null);
    setError(null);

    try {
      const response = await deleteAdminCase(caseItem.id);
      setCases((current) => current.filter(({ id }) => id !== caseItem.id));
      setSuccess(response.detail);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("You need system admin access to delete cases.");
      } else {
        setError("Could not delete the case right now.");
      }
    } finally {
      setDeletingCaseId(null);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <section className={styles.card} aria-labelledby="case-list-title">
          <div className={styles.header}>
            <div>
              <p className={styles.eyebrow}>System administration</p>
              <h1 id="case-list-title" className={styles.title}>Case directory</h1>
              <p className={styles.intro}>
                Review every submitted case, jump to the stored reference, and remove records that should no longer remain in the system.
              </p>
            </div>
            <div className={styles.summary}>
              <span className={styles.summaryLabel}>Cases</span>
              <strong className={styles.summaryValue}>{cases.length}</strong>
            </div>
          </div>

          <div className={styles.toolbar}>
            <Link to="/admin/users" className={styles.secondaryLink}>Open user directory</Link>
          </div>

          {loading && <div className={styles.banner}>Loading cases...</div>}
          {success && <div className={`${styles.banner} ${styles.bannerSuccess}`}>{success}</div>}
          {error && <div className={`${styles.banner} ${styles.bannerError}`}>{error}</div>}

          {!loading && !error && (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Case date</th>
                    <th scope="col">Flight number</th>
                    <th scope="col">Flight date</th>
                    <th scope="col">Status</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((caseItem) => (
                    <tr key={caseItem.id}>
                      <td>
                        <Link to={`/case/created/${caseItem.id}`} className={styles.caseLink}>
                          {caseItem.id}
                        </Link>
                      </td>
                      <td>{caseItem.case_date}</td>
                      <td>{caseItem.flight_number ?? "Not available"}</td>
                      <td>{caseItem.flight_date ?? "Not available"}</td>
                      <td>
                        <span className={styles.statusBadge}>{caseItem.status}</span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className={styles.dangerButton}
                          onClick={() => void handleDelete(caseItem)}
                          disabled={deletingCaseId === caseItem.id}
                        >
                          {deletingCaseId === caseItem.id ? "Deleting..." : "Delete"}
                        </button>
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