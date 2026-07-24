import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchAdminNavigation } from "../../api/auth";
import { ApiError } from "../../api/client";
import styles from "./AdminSystemPage.module.css";


export function AdminSystemPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function verifyAdminAccess() {
      try {
        await fetchAdminNavigation();
      } catch (err) {
        if (!active) {
          return;
        }
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setError("You need system admin access to view system options.");
        } else {
          setError("Could not load system options right now.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void verifyAdminAccess();

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        {loading && <div className={styles.banner}>Loading system options...</div>}
        {error && <div className={`${styles.banner} ${styles.bannerError}`}>{error}</div>}

        {!loading && !error && (
          <section className={styles.card} aria-labelledby="system-view-title">
            <p className={styles.eyebrow}>System administration</p>
            <h1 id="system-view-title" className={styles.title}>System View</h1>
            <p className={styles.intro}>
              This area is reserved for operational settings such as mail, PDF, and delivery configuration. The page is in place so admins can reach system options from the landing page as that work expands.
            </p>
            <div className={styles.actions}>
              <Link to="/admin" className={styles.primaryLink}>Back to admin view</Link>
              <Link to="/admin/users#create-user" className={styles.secondaryLink}>Create a colleague account</Link>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}