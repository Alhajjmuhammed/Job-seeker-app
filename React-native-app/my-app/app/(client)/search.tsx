import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';

interface Worker {
  id: number;
  name: string;
  category: string;
  rating: number;
  hourlyRate: number;
  completedJobs: number;
  isAvailable: boolean;
  location: string;
}

export default function ClientSearchScreen() {
  const { theme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  const categories = ['All', 'Plumbing', 'Electrical', 'Carpentry', 'Cleaning', 'Painting', 'Moving'];

  const [workers] = useState<Worker[]>([
    {
      id: 1,
      name: 'Mohammed Ali',
      category: 'Plumber',
      rating: 4.8,
      hourlyRate: 500,
      completedJobs: 143,
      isAvailable: true,
      location: 'Khartoum',
    },
    {
      id: 2,
      name: 'Ahmed Hassan',
      category: 'Electrician',
      rating: 4.9,
      hourlyRate: 600,
      completedJobs: 201,
      isAvailable: true,
      location: 'Omdurman',
    },
    {
      id: 3,
      name: 'Ibrahim Omar',
      category: 'Carpenter',
      rating: 4.7,
      hourlyRate: 550,
      completedJobs: 98,
      isAvailable: false,
      location: 'Bahri',
    },
    {
      id: 4,
      name: 'Khalid Yousif',
      category: 'Painter',
      rating: 4.6,
      hourlyRate: 450,
      completedJobs: 76,
      isAvailable: true,
      location: 'Khartoum',
    },
    {
      id: 5,
      name: 'Omar Abdullah',
      category: 'Cleaner',
      rating: 4.9,
      hourlyRate: 400,
      completedJobs: 189,
      isAvailable: true,
      location: 'Omdurman',
    },
  ]);

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
        {categories.map((category) => (
          <TouchableOpacity
            key={category}
            style={[
              styles.filterButton,
              { backgroundColor: theme.background, borderColor: theme.border },
              selectedCategory === category && { backgroundColor: theme.primary, borderColor: theme.primary },
            ]}
            onPress={() => setSelectedCategory(category)}
          >
            <Text
              style={[
                styles.filterText,
                { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' },
                selectedCategory === category && { color: theme.textLight },
              ]}
            >
              {category}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={[styles.resultsText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
          {filteredWorkers.length} worker{filteredWorkers.length !== 1 ? 's' : ''} found
        </Text>

        {filteredWorkers.map((worker) => (
          <View key={worker.id} style={[styles.workerCard, { backgroundColor: theme.card }]}>
            <View style={styles.workerInfo}>
              <View style={[styles.workerAvatar, { backgroundColor: theme.primary }]}>
                <Text style={[styles.workerAvatarText, { color: theme.textLight, fontFamily: 'Poppins_700Bold' }]}>
                  {worker.name.split(' ').map(n => n[0]).join('')}
                </Text>
              </View>
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
    borderBottomWidth: 1,
  },
  filtersContent: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 8,
    borderWidth: 1,
  },
  filterText: {
    fontSize: 13,
  },
  scrollContent: {
    padding: 20,
  },
  resultsText: {
    fontSize: 14,
    marginBottom: 16,
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
