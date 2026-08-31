import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface BrowseWorker {
  id: number;
  name: string;
  profile_image: string | null;
  bio: string;
  average_rating: string;
  completed_jobs: number;
  experience_years: number;
  city: string;
  distance_km: number | null;
  categories: { id: number; name: string }[];
}

export default function ChooseWorkerScreen() {
  const { theme } = useTheme();
  const params = useLocalSearchParams<{ categoryId: string; latitude?: string; longitude?: string }>();
  const [loading, setLoading] = useState(true);
  const [workers, setWorkers] = useState<BrowseWorker[]>([]);

  useEffect(() => {
    loadWorkers();
  }, []);

  const loadWorkers = async () => {
    try {
      setLoading(true);
      const categoryId = Number(params.categoryId);
      const lat = params.latitude ? Number(params.latitude) : null;
      const lon = params.longitude ? Number(params.longitude) : null;
      const data = await apiService.getAvailableWorkersForRequest(categoryId, lat, lon);
      setWorkers(data.workers || []);
    } catch (error) {
      console.error('Failed to load workers:', error);
      Alert.alert('Error', 'Failed to load available workers');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (worker: BrowseWorker) => {
    router.push({
      pathname: '/(client)/request-service',
      params: { preferredWorkerId: worker.id.toString(), preferredWorkerName: worker.name },
    });
  };

  const handleSkip = () => {
    router.back();
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack />

      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.text }]}>Choose a Worker</Text>
        <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
          Pick who you&apos;d like &mdash; the admin will still confirm before work starts.
        </Text>
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {workers.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="people-outline" size={56} color={theme.textSecondary} style={{ marginBottom: 16 }} />
              <Text style={[styles.emptyTitle, { color: theme.text }]}>No Workers Available Right Now</Text>
              <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
                Skip this step and let our admin assign a qualified worker for you.
              </Text>
            </View>
          ) : (
            workers.map((worker) => (
              <TouchableOpacity
                key={worker.id}
                style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}
                onPress={() => handleSelect(worker)}
              >
                {worker.profile_image ? (
                  <Image source={{ uri: worker.profile_image }} style={styles.avatar} />
                ) : (
                  <View style={[styles.avatarPlaceholder, { backgroundColor: theme.primary }]}>
                    <Text style={styles.avatarInitial}>{worker.name.charAt(0).toUpperCase()}</Text>
                  </View>
                )}
                <View style={styles.cardBody}>
                  <Text style={[styles.name, { color: theme.text }]}>{worker.name}</Text>
                  <View style={styles.metaRow}>
                    <Ionicons name="star" size={14} color="#FBBF24" />
                    <Text style={[styles.metaText, { color: theme.textSecondary }]}>
                      {worker.average_rating} &middot; {worker.completed_jobs} jobs &middot; {worker.experience_years} yrs exp
                    </Text>
                  </View>
                  <View style={styles.metaRow}>
                    <Ionicons name="location-outline" size={14} color={theme.textSecondary} />
                    <Text style={[styles.metaText, { color: theme.textSecondary }]}>
                      {worker.city || 'Unknown'}
                      {worker.distance_km !== null ? ` · ${worker.distance_km} km away` : ''}
                    </Text>
                  </View>
                  {worker.bio ? (
                    <Text style={[styles.bio, { color: theme.textSecondary }]} numberOfLines={2}>{worker.bio}</Text>
                  ) : null}
                </View>
                <Ionicons name="chevron-forward" size={20} color={theme.textTertiary} />
              </TouchableOpacity>
            ))
          )}

          <TouchableOpacity style={[styles.skipButton, { borderColor: theme.border }]} onPress={handleSkip}>
            <Text style={[styles.skipButtonText, { color: theme.textSecondary }]}>Skip &mdash; let admin choose</Text>
          </TouchableOpacity>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { padding: 20, paddingBottom: 8 },
  title: { fontSize: 22, fontFamily: 'Poppins_700Bold', marginBottom: 4 },
  subtitle: { fontSize: 13, fontFamily: 'Poppins_400Regular' },
  scrollContent: { padding: 20 },
  emptyState: { alignItems: 'center', paddingVertical: 60 },
  emptyTitle: { fontSize: 17, fontFamily: 'Poppins_600SemiBold', marginBottom: 6 },
  emptySubtitle: { fontSize: 14, fontFamily: 'Poppins_400Regular', textAlign: 'center', paddingHorizontal: 20 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    marginBottom: 12,
    gap: 12,
  },
  avatar: { width: 52, height: 52, borderRadius: 26 },
  avatarPlaceholder: { width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center' },
  avatarInitial: { color: '#FFFFFF', fontSize: 20, fontFamily: 'Poppins_700Bold' },
  cardBody: { flex: 1 },
  name: { fontSize: 15, fontFamily: 'Poppins_600SemiBold', marginBottom: 3 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 2 },
  metaText: { fontSize: 12, fontFamily: 'Poppins_400Regular' },
  bio: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginTop: 4 },
  skipButton: {
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  skipButtonText: { fontSize: 14, fontFamily: 'Poppins_600SemiBold' },
});
