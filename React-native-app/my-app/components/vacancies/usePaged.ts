/**
 * Paged list from the vacancy API ({count, next, current_page, results}).
 * Reloads every time the screen comes into focus (tab screens stay mounted),
 * and loadMore() fetches the next page while there is one.
 */
import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';

export function usePaged<T>(fetchPage: (page: number) => Promise<any>, deps: any[] = []) {
  const [items, setItems] = useState<T[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<any>(null);
  const page = useRef(1);
  const hasNext = useRef(false);
  const seq = useRef(0); // ignore answers to requests that were overtaken

  const load = useCallback(async (mode: 'first' | 'refresh' | 'more' = 'first') => {
    if (mode === 'more' && (!hasNext.current || loadingMore)) return;
    const mine = ++seq.current;
    const next = mode === 'more' ? page.current + 1 : 1;
    if (mode === 'refresh') setRefreshing(true);
    if (mode === 'more') setLoadingMore(true);
    try {
      const data = await fetchPage(next);
      if (mine !== seq.current) return;
      const results: T[] = Array.isArray(data) ? data : (data?.results || []);
      page.current = next;
      hasNext.current = !Array.isArray(data) && !!data?.next;
      setCount(Array.isArray(data) ? data.length : (data?.count ?? results.length));
      setItems(prev => (mode === 'more' ? [...prev, ...results] : results));
      setError(null);
    } catch (e) {
      if (mine === seq.current) setError(e);
    } finally {
      if (mine === seq.current) {
        setLoading(false);
        setRefreshing(false);
        setLoadingMore(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useFocusEffect(useCallback(() => { load('first'); }, [load]));

  return {
    items, count, loading, refreshing, loadingMore, error,
    refresh: () => load('refresh'),
    reload: () => { setLoading(true); load('first'); },
    loadMore: () => load('more'),
  };
}
