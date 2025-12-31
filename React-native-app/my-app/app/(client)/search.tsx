import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Image,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { useRatingRefresh } from '../../contexts/RatingContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useEffect } from 'react';

interface Worker {
  id: number;
  name: string;
  category: string;
  rating: number;
  hourlyRate: number;
  completedJobs: number;
  isAvailable: boolean;
  location: string;
  profileImage?: string | null;
}

export default function ClientSearchScreen() {
  const { theme } = useTheme();
  const { refresh } = useLocalSearchParams();
  const { refreshTrigger } = useRatingRefresh();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [categories, setCategories] = useState<string[]>(['All']);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    const loadInitial = async () => {
      try {
        setLoading(true);
        const cats = await apiService.getCategories();
        const catsList = Array.isArray(cats) ? cats : (cats.results || cats);
        if (mounted) setCategories(['All', ...catsList.map((c: any) => c.name || c)]);

        // Load workers: prefer search endpoint to get all verified workers
        const featured = await apiService.searchWorkers();
        const list = Array.isArray(featured) ? featured : (featured.results || []);
        if (mounted) {
          setWorkers(list.map((w: any) => ({
            id: w.id,
            name: w.name || (w.user?.first_name || '') + ' ' + (w.user?.last_name || ''),
            category: w.categories?.[0]?.name || 'General',
            rating: w.average_rating || 0,
            hourlyRate: w.hourly_rate || 0,
            completedJobs: w.completed_jobs_count || 0,
            isAvailable: w.availability === 'available',
            location: w.city || '',
            profileImage: w.profile_image || null,
          })));
        }
      } catch (error) {
        console.error('Error loading search data:', error);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    loadInitial();
    return () => { mounted = false; };
  }, [refresh, refreshTrigger]);

  // Additional immediate refresh when rating changes
  useEffect(() => {
    if (refreshTrigger > 0) {
      let mounted = true;
      const quickRefresh = async () => {
        try {
          const featured = await apiService.searchWorkers();
          const list = Array.isArray(featured) ? featured : (featured.results || []);
          if (mounted) {
            setWorkers(list.map((w: any) => ({
              id: w.id,
              name: w.name || 'Unknown',
              category: w.categories?.[0]?.name || 'General',
              rating: w.average_rating || 0,
              hourlyRate: parseFloat(w.hourly_rate || '0'),
              completedJobs: w.completed_jobs || 0,
              isAvailable: w.availability === 'available',
              location: w.city || '',
              profileImage: w.profile_image || null,
            })));
          }
        } catch (error) {
          console.error('Error refreshing workers:', error);
        }
      };
      quickRefresh();
      return () => { mounted = false; };
    }
  }, [refreshTrigger]);

  const filteredWorkers = workers.filter((worker) => {
    const matchesSearch = worker.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         worker.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || worker.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Find Workers" showBack={false} />

      {/* Search Bar */}
      <View style={[styles.searchContainer, { backgroundColor: theme.card, borderBottomColor: theme.border }]}>
        <View style={[styles.searchInputContainer, { backgroundColor: theme.background }]}>
          <Ionicons name="search" size={20} color={theme.textSecondary} />
          <TextInput
            style={[styles.searchInput, { color: theme.text, fontFamily: 'Poppins_400Regular' }]}
            placeholder="Search by name or category..."
            placeholderTextColor={theme.textSecondary}
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>
      </View>

      {/* Category Filters */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={[styles.filtersContainer, { backgroundColor: theme.card, borderBottomColor: theme.border }]}
        contentContainerStyle={styles.filtersContent}
      >
        <View style={{ flexDirection: 'row', gap: 6 }}>
          {categories.map((category) => (
            <TouchableOpacity
              key={category}
              style={[
                styles.filterButton,
                { backgroundColor: theme.background, borderColor: theme.border },
                selectedCategory === category && { backgroundColor: theme.primary, borderColor: theme.primary },
              ]}
              onPress={() => setSelectedCategory(category)}
              activeOpacity={0.8}
            >
              <Text
                style={[
                  styles.filterText,
                  { color: theme.textSecondary, fontFamily: 'Poppins_500Medium' },
                  selectedCategory === category && { color: theme.textLight },
                ]}
                numberOfLines={1}
              >
                {category}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Text style={[styles.resultsText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
          {filteredWorkers.length} worker{filteredWorkers.length !== 1 ? 's' : ''} found
        </Text>

        {filteredWorkers.map((worker) => (
          <View key={worker.id} style={[styles.workerCard, { backgroundColor: theme.card }]}>
            <View style={styles.workerInfo}>
              {worker.profileImage ? (
                <Image source={{ uri: worker.profileImage }} style={[styles.workerAvatar, { borderRadius: 30 }]} />
              ) : (
                <View style={[styles.workerAvatar, { backgroundColor: theme.primary }]}>
                  <Text style={[styles.workerAvatarText, { color: theme.textLight, fontFamily: 'Poppins_700Bold' }]}>
                    {(worker.name || '').split(' ').map(n => n?.[0] || '').join('')}
                  </Text>
                </View>
              )}
              <View style={styles.workerDetails}>
                <View style={styles.workerNameRow}>
                  <Text style={[styles.workerName, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>{worker.name}</Text>
                  {worker.isAvailable && (
                    <View style={styles.availableBadge}>
                      <Text style={[styles.availableBadgeText, { fontFamily: 'Poppins_600SemiBold' }]}>Available</Text>
                    </View>
                  )}
                </View>
                <Text style={[styles.workerCategory, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{worker.category}</Text>
                <View style={styles.workerLocationRow}>
                  <Ionicons name="location" size={13} color={theme.textSecondary} />
                  <Text style={[styles.workerLocation, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}> {worker.location}</Text>
                </View>
                <View style={styles.workerStats}>
                  <Ionicons name="star" size={13} color="#F59E0B" />
                  <Text style={[styles.workerRating, { fontFamily: 'Poppins_600SemiBold' }]}> {worker.rating}</Text>
                  <Text style={[styles.workerJobs, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>• {worker.completedJobs} jobs</Text>
                  <Text style={[styles.workerRate, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>• SDG {worker.hourlyRate}/hr</Text>
                </View>
              </View>
            </View>

            <View style={styles.workerActions}>
              <TouchableOpacity
                style={[styles.viewProfileButton, { backgroundColor: theme.background, borderColor: theme.border }]}
                onPress={() => router.push(`/(client)/worker/${worker.id}`)}
              >
                <Text style={[styles.viewProfileButtonText, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>View Profile</Text>
              </TouchableOpacity>
              {worker.isAvailable && (
                <TouchableOpacity
                  style={[styles.requestButton, { backgroundColor: theme.primary }]}
                  onPress={() => router.push(`/(client)/request-worker/${worker.id}` as any)}
                >
                  <Text style={[styles.requestButtonText, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Request Now</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  searchContainer: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  searchInputContainer: {
    height: 48,
    borderRadius: 12,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
  },
  filtersContainer: {
    borderBottomWidth: 0,
    maxHeight: 40,
  },
  filtersContent: {
    paddingHorizontal: 16,
    paddingVertical: 4,
    gap: 6,
  },
  filterButton: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 0,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterText: {
    fontSize: 11,
    fontWeight: '500',
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 20,
  },
  resultsText: {
    fontSize: 14,
    marginBottom: 12,
  },
  workerCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  workerInfo: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  workerAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  workerAvatarText: {
    fontSize: 20,
  },
  workerDetails: {
    flex: 1,
  },
  workerNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  workerName: {
    fontSize: 16,
    marginRight: 8,
  },
  availableBadge: {
    backgroundColor: '#D1FAE5',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  availableBadgeText: {
    fontSize: 10,
    color: '#065F46',
  },
  workerCategory: {
    fontSize: 14,
    marginBottom: 4,
  },
  workerLocationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  workerLocation: {
    fontSize: 13,
  },
  workerStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  workerRating: {
    fontSize: 13,
    color: '#F59E0B',
  },
  workerJobs: {
    fontSize: 13,
    marginLeft: 4,
  },
  workerRate: {
    fontSize: 13,
    marginLeft: 4,
  },
  workerActions: {
    flexDirection: 'row',
    gap: 8,
  },
  viewProfileButton: {
    flex: 1,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
  },
  viewProfileButtonText: {
    fontSize: 13,
  },
  requestButton: {
    flex: 1,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  requestButtonText: {
    fontSize: 13,
  },
});
