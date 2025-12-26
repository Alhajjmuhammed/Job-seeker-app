import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';

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
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Find Workers</Text>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search by name or category..."
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      {/* Category Filters */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.filtersContainer}
        contentContainerStyle={styles.filtersContent}
      >
        {categories.map((category) => (
          <TouchableOpacity
            key={category}
            style={[
              styles.filterButton,
              selectedCategory === category && styles.filterButtonActive,
            ]}
            onPress={() => setSelectedCategory(category)}
          >
            <Text
              style={[
                styles.filterText,
                selectedCategory === category && styles.filterTextActive,
              ]}
            >
              {category}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.resultsText}>
          {filteredWorkers.length} worker{filteredWorkers.length !== 1 ? 's' : ''} found
        </Text>

        {filteredWorkers.map((worker) => (
          <View key={worker.id} style={styles.workerCard}>
            <View style={styles.workerInfo}>
              <View style={styles.workerAvatar}>
                <Text style={styles.workerAvatarText}>
                  {worker.name.split(' ').map(n => n[0]).join('')}
                </Text>
              </View>
              <View style={styles.workerDetails}>
                <View style={styles.workerNameRow}>
                  <Text style={styles.workerName}>{worker.name}</Text>
                  {worker.isAvailable && (
                    <View style={styles.availableBadge}>
                      <Text style={styles.availableBadgeText}>Available</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.workerCategory}>{worker.category}</Text>
                <Text style={styles.workerLocation}>📍 {worker.location}</Text>
                <View style={styles.workerStats}>
                  <Text style={styles.workerRating}>⭐ {worker.rating}</Text>
                  <Text style={styles.workerJobs}>• {worker.completedJobs} jobs</Text>
                  <Text style={styles.workerRate}>• SDG {worker.hourlyRate}/hr</Text>
                </View>
              </View>
            </View>

            <View style={styles.workerActions}>
              <TouchableOpacity
                style={styles.viewProfileButton}
                onPress={() => router.push(`/(client)/worker/${worker.id}`)}
              >
                <Text style={styles.viewProfileButtonText}>View Profile</Text>
              </TouchableOpacity>
              {worker.isAvailable && (
                <TouchableOpacity
                  style={styles.requestButton}
                  onPress={() => router.push(`/(client)/request-worker/${worker.id}` as any)}
                >
                  <Text style={styles.requestButtonText}>Request Now</Text>
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
    backgroundColor: '#F3F4F6',
  },
  header: {
    backgroundColor: '#0F766E',
    paddingTop: 60,
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  searchContainer: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  searchInput: {
    height: 48,
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 15,
  },
  filtersContainer: {
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  filtersContent: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  filterButton: {
    backgroundColor: '#F3F4F6',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  filterButtonActive: {
    backgroundColor: '#0F766E',
    borderColor: '#0F766E',
  },
  filterText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
  },
  filterTextActive: {
    color: '#FFFFFF',
  },
  scrollContent: {
    padding: 20,
  },
  resultsText: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 16,
  },
  workerCard: {
    backgroundColor: '#FFFFFF',
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
    backgroundColor: '#0F766E',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  workerAvatarText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold',
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
    fontWeight: '600',
    color: '#1F2937',
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
    fontWeight: '600',
    color: '#065F46',
  },
  workerCategory: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 4,
  },
  workerLocation: {
    fontSize: 13,
    color: '#6B7280',
    marginBottom: 4,
  },
  workerStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  workerRating: {
    fontSize: 13,
    color: '#F59E0B',
    fontWeight: '600',
  },
  workerJobs: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 4,
  },
  workerRate: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 4,
  },
  workerActions: {
    flexDirection: 'row',
    gap: 8,
  },
  viewProfileButton: {
    flex: 1,
    height: 40,
    backgroundColor: '#F3F4F6',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  viewProfileButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
  },
  requestButton: {
    flex: 1,
    height: 40,
    backgroundColor: '#0F766E',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  requestButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});
