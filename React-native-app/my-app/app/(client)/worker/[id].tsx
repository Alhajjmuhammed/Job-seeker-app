import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams } from 'expo-router';
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
}

export default function WorkerDetailScreen() {
  const { id } = useLocalSearchParams();
  const [loading, setLoading] = useState(true);
  const [worker, setWorker] = useState<WorkerDetail | null>(null);

  useEffect(() => {
    loadWorkerDetail();
  }, [id]);

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
        location: `${workerData.city}, ${workerData.country}`,
        skills: workerData.skills?.map((s: any) => s.name) || [],
        isAvailable: workerData.availability === 'available',
        isFavorite: workerData.is_favorite || false,
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
      <View style={styles.container}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Text style={styles.backIcon}>←</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Worker Profile</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#0F766E" />
          <Text style={styles.loadingText}>Loading profile...</Text>
        </View>
      </View>
    );
  }

  if (!worker) {
    return (
      <View style={styles.container}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Text style={styles.backIcon}>←</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Worker Profile</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>👤</Text>
          <Text style={styles.emptyText}>Worker not found</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backIcon}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Worker Profile</Text>
        <TouchableOpacity onPress={handleToggleFavorite} style={styles.favoriteButton}>
          <Text style={styles.favoriteIcon}>{worker.isFavorite ? '❤️' : '🤍'}</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Profile Section */}
        <View style={styles.profileSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{worker.name[0]}</Text>
          </View>
          <Text style={styles.workerName}>{worker.name}</Text>
          <Text style={styles.workerCategory}>{worker.category}</Text>
          
          {/* Availability Badge */}
          <View style={[styles.availabilityBadge, worker.isAvailable && styles.availableBadge]}>
            <Text style={[styles.availabilityText, worker.isAvailable && styles.availableText]}>
              {worker.isAvailable ? '✓ Available' : '✗ Busy'}
            </Text>
          </View>

          {/* Stats */}
          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>⭐ {worker.rating.toFixed(1)}</Text>
              <Text style={styles.statLabel}>Rating</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{worker.completedJobs}</Text>
              <Text style={styles.statLabel}>Jobs Done</Text>
            </View>
          </View>
        </View>

        {/* Rate Card */}
        <View style={styles.rateCard}>
          <Text style={styles.rateLabel}>Hourly Rate</Text>
          <Text style={styles.rateAmount}>SDG {worker.hourlyRate}/hr</Text>
        </View>

        {/* Bio Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          <Text style={styles.bioText}>{worker.bio}</Text>
        </View>

        {/* Location */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Location</Text>
          <View style={styles.locationRow}>
            <Text style={styles.locationIcon}>📍</Text>
            <Text style={styles.locationText}>{worker.location}</Text>
          </View>
        </View>

        {/* Skills */}
        {worker.skills.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Skills</Text>
            <View style={styles.skillsContainer}>
              {worker.skills.map((skill, index) => (
                <View key={index} style={styles.skillBadge}>
                  <Text style={styles.skillText}>{skill}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </ScrollView>

      {/* Action Buttons */}
      <View style={styles.bottomSection}>
        <TouchableOpacity
          style={styles.messageButton}
          onPress={handleMessageWorker}
        >
          <Text style={styles.messageButtonText}>💬 Message Worker</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.requestButton}
          onPress={handleRequestDirectly}
        >
          <Text style={styles.requestButtonText}>Request Directly</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F4F6',
  },
  header: {
    backgroundColor: '#0F766E',
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
  backIcon: {
    fontSize: 28,
    color: '#FFFFFF',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  favoriteButton: {
    width: 40,
    alignItems: 'flex-end',
  },
  favoriteIcon: {
    fontSize: 24,
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
    color: '#6B7280',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyText: {
    fontSize: 18,
    color: '#6B7280',
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  profileSection: {
    backgroundColor: '#FFFFFF',
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
    backgroundColor: '#0F766E',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarText: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  workerName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 4,
  },
  workerCategory: {
    fontSize: 16,
    color: '#6B7280',
    marginBottom: 12,
  },
  availabilityBadge: {
    backgroundColor: '#FEE2E2',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginBottom: 20,
  },
  availableBadge: {
    backgroundColor: '#D1FAE5',
  },
  availabilityText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#991B1B',
  },
  availableText: {
    color: '#065F46',
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingTop: 20,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: '#E5E7EB',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  rateCard: {
    backgroundColor: '#FFFFFF',
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
    color: '#6B7280',
    marginBottom: 4,
  },
  rateAmount: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#0F766E',
  },
  section: {
    backgroundColor: '#FFFFFF',
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
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 12,
  },
  bioText: {
    fontSize: 15,
    color: '#4B5563',
    lineHeight: 24,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  locationIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  locationText: {
    fontSize: 16,
    color: '#4B5563',
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
    fontWeight: '600',
    color: '#0369A1',
  },
  bottomSection: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#FFFFFF',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
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
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#0F766E',
  },
  messageButtonText: {
    color: '#0F766E',
    fontSize: 16,
    fontWeight: 'bold',
  },
  requestButton: {
    flex: 1,
    backgroundColor: '#0F766E',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  requestButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
