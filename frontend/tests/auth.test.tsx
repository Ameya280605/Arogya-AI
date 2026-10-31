import { describe, it, beforeEach } from "node:test";
import assert from "node:assert";
import {
  getStoredUser,
  getStoredToken,
  setStoredUser,
  setStoredToken,
  clearStoredToken,
  onAuthChange,
  type UserSummary,
} from "../services/auth";

describe("Authentication Snapshot Stability & Cache", () => {
  // Mock localStorage for node environment if not present
  const storageMap = new Map<string, string>();
  const mockLocalStorage = {
    getItem: (key: string) => storageMap.get(key) ?? null,
    setItem: (key: string, val: string) => storageMap.set(key, val),
    removeItem: (key: string) => storageMap.delete(key),
    clear: () => storageMap.clear(),
  };

  beforeEach(() => {
    storageMap.clear();
    // Ensure global window / localStorage exist for unit test
    if (typeof globalThis.window === "undefined") {
      (globalThis as unknown as { window: unknown }).window = {
        localStorage: mockLocalStorage,
        dispatchEvent: () => true,
        addEventListener: () => {},
        removeEventListener: () => {},
      };
    } else if (!globalThis.window.localStorage) {
      (globalThis.window as unknown as { localStorage: unknown }).localStorage = mockLocalStorage;
    }
    clearStoredToken();
  });

  it("returns null when no user is stored", () => {
    assert.strictEqual(getStoredUser(), null);
    assert.strictEqual(getStoredToken(), null);
  });

  it("returns the exact same object reference on consecutive getStoredUser calls (preventing infinite loops)", () => {
    const user: UserSummary = {
      id: "usr-12345",
      username: "doctor_tester",
      email: "doctor@arogya.local",
      full_name: "Dr. Tester",
      role: "doctor_reviewer",
      is_active: true,
    };

    setStoredUser(user);

    const ref1 = getStoredUser();
    const ref2 = getStoredUser();
    const ref3 = getStoredUser();

    assert.ok(ref1 !== null);
    // Object identity must match exactly for useSyncExternalStore getSnapshot
    assert.strictEqual(ref1, ref2, "Snapshot reference must be identical across calls");
    assert.strictEqual(ref2, ref3, "Snapshot reference must be identical across calls");
    assert.strictEqual(ref1?.username, "doctor_tester");
  });

  it("returns the exact same cached reference when read directly from localStorage", () => {
    const rawUserData = JSON.stringify({
      id: "usr-9999",
      username: "admin_tester",
      email: "admin@arogya.local",
      full_name: "Admin Tester",
      role: "administrator",
      is_active: true,
    });

    mockLocalStorage.setItem("arogya_ai_user", rawUserData);

    const snapshotA = getStoredUser();
    const snapshotB = getStoredUser();

    assert.ok(snapshotA !== null);
    assert.strictEqual(snapshotA, snapshotB, "Repeated reads from storage must yield cached reference");
    assert.strictEqual(snapshotA?.id, "usr-9999");
  });

  it("registers and unregisters onAuthChange subscribers cleanly", () => {
    let callCount = 0;
    let receivedUser: UserSummary | null = null;

    const unsubscribe = onAuthChange((user) => {
      callCount++;
      receivedUser = user;
    });

    const testUser: UserSummary = {
      id: "usr-listener",
      username: "researcher_1",
      email: "researcher@arogya.local",
      full_name: "Researcher One",
      role: "researcher",
      is_active: true,
    };

    setStoredUser(testUser);
    assert.strictEqual(callCount, 1);
    assert.strictEqual((receivedUser as UserSummary | null)?.username, "researcher_1");

    // Unsubscribe and verify no more calls
    unsubscribe();
    clearStoredToken();
    assert.strictEqual(callCount, 1, "Unsubscribed listener should not receive subsequent notifications");
  });

  it("clears cached snapshots and notifies subscribers when session is terminated", () => {
    let notifiedUser: UserSummary | null = { id: "old", email: "old@test.com", full_name: null, is_active: true };

    const unsubscribe = onAuthChange((user) => {
      notifiedUser = user;
    });

    setStoredToken("test-jwt-token");
    setStoredUser({
      id: "usr-active",
      username: "active_user",
      email: "active@arogya.local",
      full_name: "Active User",
      role: "clinician",
      is_active: true,
    });

    assert.strictEqual(getStoredToken(), "test-jwt-token");
    assert.strictEqual(getStoredUser()?.username, "active_user");

    clearStoredToken();

    assert.strictEqual(getStoredToken(), null);
    assert.strictEqual(getStoredUser(), null);
    assert.strictEqual(notifiedUser, null);

    unsubscribe();
  });
});
