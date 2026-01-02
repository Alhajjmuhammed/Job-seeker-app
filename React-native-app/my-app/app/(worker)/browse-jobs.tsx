import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  RefreshControl,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface Job {
  id: number;
  title: string;
  category_name: string;
  client_name: string;
  budget: number;
  duration_type: string;
  city: string;
  created_at: string;
  application_count: number;
}

interface Category {
  id: number;
  name: string;
}

export default function BrowseJobsScreen() {
  const { theme, isDark } = useTheme();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [savedJobs, setSavedJobs] = useState<Set<number>>(new Set());
  
  // Search and Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [minBudget, setMinBudget] = useState('');
  const [maxBudget, setMaxBudget] = useState('');
  const [location, setLocation] = useState('');
  const [durationType, setDurationType] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Check if professional worker
  const isProfessional = user?.workerType === 'professional';

  useEffect(() => {
    if (!isProfessional) {
      router.replace('/jobs');
      return;
    }
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [jobsData, categoriesData, savedJobsData] = await Promise.all([
        apiService.getBrowseJobs(),
        apiService.getCategories(),
        apiService.getSavedJobs(),
      ]);
      
      setJobs(jobsData);
      setCategories(categoriesData);
      
      // Extract saved job IDs
      const savedIds = new Set<number>(savedJobsData.saved_jobs?.map((s: any) => s.job.id as number) || []);
      setSavedJobs(savedIds);
    } catch (error) {
      console.error('Error loading jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadJobs = async () => {
    try {
      const params: any = {};
      
      if (selectedCategory) params.category = selectedCategory;
      if (location) params.city = location;
      
      const jobsData = await apiService.getBrowseJobs(params);
      setJobs(jobsData);
    } catch (error) {
      console.error('Error loading jobs:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadJobs();
    setRefreshing(false);
  };

  const applyFilters = () => {
    setShowFilters(false);
    loadJobs();
  };

  const clearFilters = () => {
    setSelectedCategory(null);
    setMinBudget('');
    setMaxBudget('');
    setLocation('');
    setDurationType(null);
    setShowFilters(false);
    loadJobs();
  };

  const handleToggleSaveJob = async (jobId: number) => {
    try {
      const isSaved = savedJobs.has(jobId);
      
      if (isSaved) {
        await apiService.unsaveJob(jobId);
        setSavedJobs(prev => {
          const next = new Set(prev);
          next.delete(jobId);
          return next;
        });
      } else {
        await apiService.saveJob(jobId);
        setSavedJobs(prev => new Set([...prev, jobId]));
      }
    } catch (error) {
      console.error('Error toggling saved job:', error);
    }
  };

  const filteredJobs = jobs.filter(job => {
    // Client-side filtering for budget and search
    if (searchQuery && !job.title.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (minBudget && job.budget < parseFloat(minBudget)) {
      return false;
    }
    if (maxBudget && job.budget > parseFloat(maxBudget)) {
      return false;
    }
    if (durationType && job.duration_type !== durationType) {
      return false;
    }
    return true;
  });

  const renderJobCard = (job: Job) => {
    const isSaved = savedJobs.has(job.id);
    
    return (
      <View
        key={job.id}
        style={[styles.jobCard, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}
      >
        <TouchableOpacity
          style={styles.jobCardContent}
          onPress={() => router.push(`/job/${job.id}` as any)}
        >
          <View style={styles.jobHeader}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.jobTitle, { color: theme.text }]} numberOfLines={2}>
                {job.title}
              </Text>
              <View style={[styles.categoryBadge, { backgroundColor: isDark ? 'rgba(15, 118, 110, 0.2)' : '#F0FDF4' }]}>
                <Text style={[styles.categoryText, { color: theme.primary }]}>{job.category_name}</Text>
              </View>
            </View>
          </View>

          <View style={styles.jobMeta}>
            <View style={styles.metaItem}>
              <Ionicons name="business-outline" size={16} color={theme.textSecondary} />
              <Text style={[styles.metaText, { color: theme.textSecondary }]}>{job.client_name}</Text>
            </View>
            
            <View style={styles.metaItem}>
              <Ionicons name="location-outline" size={16} color={theme.textSecondary} />
              <Text style={[styles.metaText, { color: theme.textSecondary }]}>{job.city || 'Remote'}</Text>
            </View>
          </View>

          <View style={styles.jobFooter}>
            <View style={styles.budgetContainer}>
              <Text style={[styles.budgetAmount, { color: theme.primary }]}>
                ${job.budget}
              </Text>
              <Text style={[styles.budgetType, { color: theme.textSecondary }]}>
                /{job.duration_type}
              </Text>
            </View>

            <View style={styles.applicantsContainer}>
              <Ionicons name="people-outline" size={16} color={theme.textSecondary} />
              <Text style={[styles.applicantsText, { color: theme.textSecondary }]}>
                {job.application_count || 0} applicants
              </Text>
            </View>
          </View>
        </TouchableOpacity>
        
        {/* Save/Unsave Button */}
        <TouchableOpacity
          style={styles.saveButton}
          onPress={() => handleToggleSaveJob(job.id)}
        >
          <Ionicons 
            name={isSaved ? "heart" : "heart-outline"} 
            size={24} 
            color={isSaved ? "#EF4444" : theme.textSecondary} 
          />
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack />

      <View style={styles.content}>
        {/* Search Bar */}
        <View style={styles.searchContainer}>
          <View style={[styles.searchBar, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <Ionicons name="search" size={20} color={theme.textSecondary} />
            <TextInput
              style={[styles.searchInput, { color: theme.text }]}
              value={searchQuery}
              onChangeText={setSearchQuery}
              placeholder="Search jobs..."
              placeholderTextColor={theme.textSecondary}
            />
          </View>
          
          <TouchableOpacity
            style={[styles.filterButton, { backgroundColor: theme.primary }]}
            onPress={() => setShowFilters(true)}
          >
            <Ionicons name="options-outline" size={24} color="#FFFFFF" />
            {(selectedCategory || minBudget || maxBudget || location || durationType) && (
              <View style={styles.filterBadge}>
                <Text style={styles.filterBadgeText}>•</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>

        {/* Jobs List */}
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.primary} />
            <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading jobs...</Text>
          </View>
        ) : (
          <ScrollView
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={theme.primary}
                colors={[theme.primary]}
              />
            }
          >
            {filteredJobs.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="briefcase-outline" size={56} color={theme.textSecondary} style={{ marginBottom: 16 }} />
                <Text style={[styles.emptyTitle, { color: theme.text }]}>No Jobs Found</Text>
                <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
                  Try adjusting your search or filters
                </Text>
              </View>
            ) : (
              <>
                <Text style={[styles.resultCount, { color: theme.textSecondary }]}>
                  {filteredJobs.length} {filteredJobs.length === 1 ? 'job' : 'jobs'} found
                </Text>
                {filteredJobs.map(renderJobCard)}
              </>
            )}
          </ScrollView>
        )}
      </View>

      {/* Filter Modal */}
      <Modal
        visible={showFilters}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowFilters(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: theme.surface }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: theme.text }]}>Filters</Text>
              <TouchableOpacity onPress={() => setShowFilters(false)}>
                <Ionicons name="close" size={28} color={theme.text} />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.filterScroll} contentContainerStyle={styles.filterScrollContent}>
              {/* Category Filter */}
              <View style={styles.filterSection}>
                <Text style={[styles.filterLabel, { color: theme.text }]}>Category</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View style={styles.chipContainer}>
                    <TouchableOpacity
                      style={[
                        styles.chip,
                        { borderColor: theme.border },
                        !selectedCategory && [styles.chipActive, { backgroundColor: theme.primary, borderColor: theme.primary }]
                      ]}
                      onPress={() => setSelectedCategory(null)}
                    >
                      <Text style={[styles.chipText, { color: !selectedCategory ? '#FFFFFF' : theme.text }]}>
                        All
                      </Text>
                    </TouchableOpacity>
                    {categories.map(category => (
                      <TouchableOpacity
                        key={category.id}
                        style={[
                          styles.chip,
                          { borderColor: theme.border },
                          selectedCategory === category.id && [styles.chipActive, { backgroundColor: theme.primary, borderColor: theme.primary }]
                        ]}
                        onPress={() => setSelectedCategory(category.id)}
                      >
                        <Text style={[styles.chipText, { color: selectedCategory === category.id ? '#FFFFFF' : theme.text }]}>
                          {category.name}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </ScrollView>
              </View>

              {/* Budget Range */}
              <View style={styles.filterSection}>
                <Text style={[styles.filterLabel, { color: theme.text }]}>Budget Range</Text>
                <View style={styles.rangeInputs}>
                  <TextInput
                    style={[styles.rangeInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
                    value={minBudget}
                    onChangeText={setMinBudget}
                    placeholder="Min"
                    placeholderTextColor={theme.textSecondary}
                    keyboardType="numeric"
                  />
                  <Text style={[styles.rangeSeparator, { color: theme.textSecondary }]}>to</Text>
                  <TextInput
                    style={[styles.rangeInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
                    value={maxBudget}
                    onChangeText={setMaxBudget}
                    placeholder="Max"
                    placeholderTextColor={theme.textSecondary}
                    keyboardType="numeric"
                  />
                </View>
              </View>

              {/* Duration Type */}
              <View style={styles.filterSection}>
                <Text style={[styles.filterLabel, { color: theme.text }]}>Duration Type</Text>
                <View style={styles.chipContainer}>
                  {['hourly', 'daily', 'weekly', 'monthly', 'project'].map(type => (
                    <TouchableOpacity
                      key={type}
                      style={[
                        styles.chip,
                        { borderColor: theme.border },
                        durationType === type && [styles.chipActive, { backgroundColor: theme.primary, borderColor: theme.primary }]
                      ]}
                      onPress={() => setDurationType(durationType === type ? null : type)}
                    >
                      <Text style={[styles.chipText, { color: durationType === type ? '#FFFFFF' : theme.text }]}>
                        {type.charAt(0).toUpperCase() + type.slice(1)}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>

              {/* Location */}
              <View style={styles.filterSection}>
                <Text style={[styles.filterLabel, { color: theme.text }]}>Location</Text>
                <TextInput
                  style={[styles.locationInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
                  value={location}
                  onChangeText={setLocation}
                  placeholder="Enter city or location"
                  placeholderTextColor={theme.textSecondary}
                />
              </View>
            </ScrollView>

            {/* Modal Actions */}
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.clearButton, { borderColor: theme.border }]}
                onPress={clearFilters}
              >
                <Text style={[styles.clearButtonText, { color: theme.textSecondary }]}>Clear All</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.applyButton, { backgroundColor: theme.primary }]}
                onPress={applyFilters}
              >
                <Text style={styles.applyButtonText}>Apply Filters</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  searchContainer: {
    flexDirection: 'row',
    gap: 12,
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  searchBar: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    height: 48,
    paddingHorizontal: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  filterButton: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  filterBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#EF4444',
  },
  filterBadgeText: {
    color: '#EF4444',
    fontSize: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingTop: 0,
  },
  resultCount: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 16,
  },
  jobCard: {
    borderRadius: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    position: 'relative',
  },
  jobCardContent: {
    padding: 20,
  },
  saveButton: {
    position: 'absolute',
    top: 16,
    right: 16,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  jobHeader: {
    marginBottom: 12,
  },
  jobTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 8,
  },
  categoryBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  categoryText: {
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
  },
  jobMeta: {
    gap: 8,
    marginBottom: 12,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaText: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  jobFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
  budgetContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  budgetAmount: {
    fontSize: 24,
    fontFamily: 'Poppins_700Bold',
  },
  budgetType: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  applicantsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  applicantsText: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 6,
  },
  emptySubtitle: {
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
    textAlign: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  modalTitle: {
    fontSize: 20,
    fontFamily: 'Poppins_700Bold',
  },
  filterScroll: {
    flex: 1,
  },
  filterScrollContent: {
    padding: 20,
  },
  filterSection: {
    marginBottom: 24,
  },
  filterLabel: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 12,
  },
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
  },
  chipActive: {},
  chipText: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  rangeInputs: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  rangeInput: {
    flex: 1,
    height: 48,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  rangeSeparator: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  locationInput: {
    height: 48,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
  clearButton: {
    flex: 1,
    height: 48,
    borderRadius: 12,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  clearButtonText: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  applyButton: {
    flex: 1,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  applyButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
});
