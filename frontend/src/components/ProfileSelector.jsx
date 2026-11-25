import { useEffect, useState } from "react";

import { getProfiles } from "../services/api.js";

const STORAGE_KEY = "learning.dsaProfileId";

export function getStoredProfileId() {
  const profileId = localStorage.getItem(STORAGE_KEY);
  return profileId || "PROFILE-DSA";
}

export function hasStoredProfile() {
  return Boolean(localStorage.getItem(STORAGE_KEY));
}

export function setStoredProfileId(profileId) {
  if (profileId) localStorage.setItem(STORAGE_KEY, profileId);
}

export default function ProfileSelector({ activeProfileId, onChange }) {
  const [profiles, setProfiles] = useState([]);

  useEffect(() => {
    async function loadProfiles() {
      try {
        setProfiles(await getProfiles());
      } catch (err) {
        setProfiles([]);
      }
    }

    loadProfiles();
  }, []);

  return (
    <label className="flex flex-wrap items-center gap-2 text-sm font-semibold text-muted">
      Current Profile:
      <select
        className="rounded-lg border border-line bg-white px-3 py-2 font-bold text-ink"
        value={activeProfileId}
        onChange={(event) => {
          setStoredProfileId(event.target.value);
          onChange(event.target.value);
        }}
      >
        {profiles.length ? profiles.map((profile) => (
          <option key={profile.profile_id} value={profile.profile_id}>
            {profile.label}
          </option>
        )) : (
          <option value={activeProfileId}>{activeProfileId}</option>
        )}
      </select>
    </label>
  );
}
