import { useState, useEffect, useCallback } from 'react';
import { Account } from '../types/account';
import { fetchAccounts, ApiError } from '../api/client';

export function useAccounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadAccounts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAccounts();
      setAccounts(data);
      // Auto-select Primary Checking or first account on initial load
      setSelectedAccountId((prev) => {
        if (prev && data.some((a) => a.id === prev)) return prev;
        const defaultAccount = data.find((a) => a.id === 'CHK-1001') || data[0];
        return defaultAccount ? defaultAccount.id : null;
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load accounts. Please check connection.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const selectAccount = useCallback((id: string) => {
    setSelectedAccountId(id);
  }, []);

  return {
    accounts,
    selectedAccountId,
    selectedAccount: accounts.find((a) => a.id === selectedAccountId) || null,
    loading,
    error,
    selectAccount,
    refreshAccounts: loadAccounts,
  };
}
