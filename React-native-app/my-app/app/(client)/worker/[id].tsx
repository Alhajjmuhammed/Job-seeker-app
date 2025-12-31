import React, { useState, useEffect, useCallback } from 'react';
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
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import { useRatingRefresh } from '../../../contexts/RatingContext';
import apiService from '../../../services/api';

interface WorkerDetail {
  id: number;
  name: string;
  category: string;
  rating: number;
  hourlyRate: number;
  completedJobs: number;
  bio: string;
  location: string;
  skills: string[];
  isAvailable: boolean;
  isFavorite: boolean;
  profileImage?: string | null;
}

export default function WorkerDetailScreen() {
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const { refreshTrigger } = useRatingRefresh();
  const [loading, setLoading] = useState(true);
  const [worker, setWorker] = useState<WorkerDetail | null>(null);

  useEffect(() => {
    loadWorkerDetail();
  }, [id]);

  // Refresh data when screen comes into focus (e.g., after rating)
  useFocusEffect(
    useCallback(() => {
      loadWorkerDetail();
    }, [id, refreshTrigger])
  );

  // Additional immediate refresh when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger > 0) {
      loadWorkerDetail();
    }
  }, [refreshTrigger]);

  const loadWorkerDetail = async () => {
    try {
      setLoading(true);
      const workerData = await apiService.getWorkerDetail(Number(id));
      setWorker({
        id: workerData.id,
        name: workerData.name,
        category: workerData.categories?.[0]?.name || 'General',
        rating: workerData.average_rating || 0,
        hourlyRate: parseFloat(workerData.hourly_rate || '0'),
        completedJobs: workerData.completed_jobs || 0,
        bio: workerData.bio || 'No bio available',
        location: [workerData.city, workerData.state, workerData.country].filter(Boolean).join(', ') || 'Location not specified',
        skills: workerData.skills?.map((s: any) => s.name) || [],
        isAvailable: workerData.availability === 'available',
        isFavorite: workerData.is_favorite || false,
        profileImage: workerData.profile_image || null,
      });
    } catch (error) {
      console.error('Error loading worker:', error);
      Alert.alert('Error', 'Failed to load worker details');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFavorite = async () => {
    try {
      await apiService.toggleFavoriteWorker(Number(id));
      setWorker(worker ? { ...worker, isFavorite: !worker.isFavorite } : null);
    } catch (error) {
      Alert.alert('Error', 'Failed to update favorite');
    }
  };

  const handleRequestDirectly = () => {
    router.push(`/(client)/request-worker/${id}` as any);
  };

  const handleMessageWorker = () => {
    router.push(`/(client)/conversation/${id}?name=${worker?.name}` as any);
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={[styles.header, { backgroundColor: theme.primary }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color={theme.textLight} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Worker Profile</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Loading profile...</Text>
        </View>
      </View>
    );
  }

  if (!worker) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={[styles.header, { backgroundColor: theme.primary }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color={theme.textLight} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Worker Profile</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.emptyContainer}>
          <Ionicons name="person-outline" size={64} color={theme.textSecondary} />
          <Text style={[styles.emptyText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Worker not found</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: theme.primary }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={theme.textLight} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Worker Profile</Text>
        <TouchableOpacity onPress={handleToggleFavorite} style={styles.favoriteButton}>
          <Ionicons 
            name={worker.isFavorite ? "heart" : "heart-outline"} 
            size={24} 
            color={worker.isFavorite ? "#EF4444" : theme.textLight} 
          />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Profile Section */}
        <View style={[styles.profileSection, { backgroundColor: theme.card }]}>
          {worker.profileImage ? (
            <Image source={{ uri: worker.profileImage }} style={styles.avatarImage} />
          ) : (
            <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
              <Text style={[styles.avatarText, { color: theme.textLight, fontFamily: 'Poppins_700Bold' }]}>
                {worker.name?.[0] || ''}
              </Text>
            </View>
          )}
          <Text style={[styles.workerName, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>{worker.name}</Text>
          <Text style={[styles.workerCategory, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{worker.category}</Text>
          
          {/* Availability Badge */}
          <View style={[
            styles.availabilityBadge, 
            { backgroundColor: worker.isAvailable ? '#D1FAE5' : '#FEE2E2' }
          ]}>
            <Ionicons 
              name={worker.isAvailable ? "checkmark-circle" : "close-circle"} 
              size={16} 
              color={worker.isAvailable ? '#065F46' : '#991B1B'} 
            />
            <Text style={[
              styles.availabilityText, 
              { color: worker.isAvailable ? '#065F46' : '#991B1B', fontFamily: 'Poppins_600SemiBold' }
            ]}>
              {worker.isAvailable ? 'Available' : 'Busy'}
            </Text>
          </View>

          {/* Stats */}
          <View style={[styles.statsRow, { borderTopColor: theme.border }]}>
            <View style={styles.statItem}>
              <View style={styles.statValueRow}>
                <Ionicons name="star" size={20} color="#FCD34D" />
                <Text style={[styles.statValue, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>
                  {(Number(worker.rating) || 0).toFixed(1)}
                </Text>
              </View>
              <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Rating</Text>
            </View>
            <View style={[styles.statDivider, { backgroundColor: theme.border }]} />
            <View style={styles.statItem}>
              <Text style={[styles.statValue, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>{worker.completedJobs}</Text>
              <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Jobs Done</Text>
            </View>
          </View>
        </View>

        {/* Rate Card */}
        <View style={[styles.rateCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.rateLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Hourly Rate</Text>
          <Text style={[styles.rateAmount, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>
            SDG {worker.hourlyRate}/hr
          </Text>
        </View>

        {/* Bio Section */}
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>About</Text>
          <Text style={[styles.bioText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{worker.bio}</Text>
        </View>

        {/* Location */}
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>Location</Text>
          <View style={styles.locationRow}>
            <Ionicons name="location" size={20} color={theme.primary} />
            <Text style={[styles.locationText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{worker.location}</Text>
          </View>
        </View>

        {/* Skills */}
        {worker.skills.length > 0 && (
          <View style={[styles.section, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>Skills</Text>
            <View style={styles.skillsContainer}>
              {worker.skills.map((skill, index) => (
                <View key={index} style={styles.skillBadge}>
                  <Text style={[styles.skillText, { fontFamily: 'Poppins_600SemiBold' }]}>{skill}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </ScrollView>

      {/* Action Buttons */}
      <View style={[styles.bottomSection, { backgroundColor: theme.card, borderTopColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.messageButton, { borderColor: theme.primary }]}
          onPress={handleMessageWorker}
          activeOpacity={0.8}
        >
          <Ionicons name="chatbubble-outline" size={20} color={theme.primary} />
          <Text style={[styles.messageButtonText, { color: theme.primary, fontFamily: 'Poppins_600SemiBold' }]}>
            Message
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.rateButton, { backgroundColor: '#FCD34D' }]}
          onPress={() => router.push(`/(client)/rate-worker/${id}?workerName=${worker?.name}` as any)}
          activeOpacity={0.8}
        >
          <Ionicons name="star" size={22} color="#D97706" />
          <Text style={[styles.rateButtonText, { color: '#92400E', fontFamily: 'Poppins_700Bold' }]}>
            Rate
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.requestButton, { backgroundColor: theme.primary }]}
          onPress={handleRequestDirectly}
          activeOpacity={0.8}
        >
          <Text style={[styles.requestButtonText, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>
            Request
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    width: 40,
  },
  headerTitle: {
    fontSize: 20,
  },
  favoriteButton: {
    width: 40,
    alignItems: 'flex-end',
  },
  headerRight: {
    width: 40,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyText: {
    fontSize: 18,
    marginTop: 16,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  profileSection: {
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    marginBottom: 20,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
    marginBottom: 16,
  },
  avatarText: {
    fontSize: 40,
  },
  workerName: {
    fontSize: 24,
    marginBottom: 4,
  },
  workerCategory: {
    fontSize: 16,
    marginBottom: 12,
  },
  availabilityBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginBottom: 20,
  },
  availabilityText: {
    fontSize: 14,
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    borderTopWidth: 1,
    paddingTop: 20,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 4,
  },
  statDivider: {
    width: 1,
    height: 40,
  },
  statValue: {
    fontSize: 20,
  },
  statLabel: {
    fontSize: 14,
  },
  rateCard: {
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  rateLabel: {
    fontSize: 14,
    marginBottom: 4,
  },
  rateAmount: {
    fontSize: 28,
  },
  section: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  sectionTitle: {
    fontSize: 18,
    marginBottom: 12,
  },
  bioText: {
    fontSize: 15,
    lineHeight: 24,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  locationText: {
    fontSize: 16,
  },
  skillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillBadge: {
    backgroundColor: '#E0F2FE',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  skillText: {
    fontSize: 14,
    color: '#0369A1',
  },
  bottomSection: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    borderTopWidth: 1,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    flexDirection: 'row',
    gap: 12,
  },
  messageButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 16,
    padding: 16,
    borderWidth: 2,
  },
  messageButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  rateButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 16,
    padding: 16,
    backgroundColor: '#FCD34D',
    elevation: 4,
    shadowColor: '#F59E0B',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    borderWidth: 1,
    borderColor: '#F59E0B',
    transform: [{ scale: 1 }],
  },
  rateButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#92400E',
  },
  requestButton: {
    flex: 1,
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
  },
  requestButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
});
