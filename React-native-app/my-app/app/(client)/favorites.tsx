import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface FavoriteWorker {
  id: number;
  worker_id: number;
  worker_name: string;
  worker_username: string;
  categories: string[];
  rating: number;
  total_reviews: number;
  completed_jobs: number;
  hourly_rate: number;
  daily_rate: number;
  availability: string;
  bio: string;
  city: string;
  profile_picture: string | null;
  added_at: string;
}

export default function FavoritesScreen() {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [favorites, setFavorites] = useState<FavoriteWorker[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useFocusEffect(
    useCallback(() => {
      loadFavorites();
    }, [])
  );

  const loadFavorites = async (pageNum: number = 1, append: boolean = false) => {
    try {
      if (!append) setLoading(true);
      
      const data = await apiService.getFavorites(pageNum);
      
      if (append) {
        setFavorites(prev => [...prev, ...(data.results || [])]);
      } else {
        setFavorites(data.results || []);
      }
      
      setHasMore(!!data.next);
      setPage(pageNum);
    } catch (error) {
      console.error('Error loading favorites:', error);
      Alert.alert(t('common.error'), t('favoriteWorkers.failedLoadFavorites'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadFavorites(1, false);
  };

  const handleLoadMore = () => {
    if (!loading && hasMore) {
      loadFavorites(page + 1, true);
    }
  };

  const handleRemoveFavorite = async (workerId: number, workerName: string) => {
    Alert.alert(
      'Remove Favorite',
      `Remove ${workerName} from your favorites?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiService.toggleFavorite(workerId);
              setFavorites(prev => prev.filter(f => f.worker_id !== workerId));
              Alert.alert(t('common.success'), `${workerName} removed from favorites`);
            } catch (error) {
              console.error('Error removing favorite:', error);
              Alert.alert(t('common.error'), t('favoriteWorkers.failedRemoveFavorite'));
            }
          },
        },
      ]
    );
  };

  const handleWorkerPress = (workerId: number) => {
    // Navigate to worker detail once that screen is implemented
    Alert.alert(t('favoriteWorkers.workerDetails'), `Worker ID: ${workerId}\n\nWorker detail screen coming soon`);
  };

  const getAvailabilityColor = (availability: string) => {
    switch (availability) {
      case 'available':
        return '#10B981';
      case 'busy':
        return '#F59E0B';
      case 'unavailable':
        return '#EF4444';
      default:
        return theme.textSecondary;
    }
  };

  const getAvailabilityText = (availability: string) => {
    switch (availability) {
      case 'available':
        return 'Available';
      case 'busy':
        return 'Busy';
      case 'unavailable':
        return 'Unavailable';
      default:
        return availability;
    }
  };

  const renderWorkerCard = ({ item }: { item: FavoriteWorker }) => (
    <TouchableOpacity
      style={[styles.workerCard, { backgroundColor: theme.card }]}
      onPress={() => handleWorkerPress(item.worker_id)}
    >
      {/* Header with image and name */}
      <View style={styles.workerHeader}>
        {item.profile_picture ? (
          <Image
            source={{ uri: item.profile_picture }}
            style={styles.workerImage}
          />
        ) : (
          <View style={[styles.workerImage, styles.defaultAvatar, { backgroundColor: theme.primary + '20' }]}>
            <Ionicons name="person" size={32} color={theme.primary} />
          </View>
        )}
        
        <View style={styles.workerInfo}>
          <Text style={[styles.workerName, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
            {item.worker_name}
          </Text>
          
          {/* Rating */}
          {item.rating > 0 && (
            <View style={styles.ratingContainer}>
              <Ionicons name="star" size={16} color="#F59E0B" />
              <Text style={[styles.ratingText, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
                {item.rating.toFixed(1)}
              </Text>
              <Text style={[styles.reviewsText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                ({item.total_reviews} reviews)
              </Text>
            </View>
          )}
          
          {/* Location & Availability */}
          <View style={styles.locationRow}>
            {item.city && (
              <View style={styles.cityContainer}>
                <Ionicons name="location" size={14} color={theme.textSecondary} />
                <Text style={[styles.cityText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                  {item.city}
                </Text>
              </View>
            )}
            
            <View style={[styles.availabilityBadge, { backgroundColor: getAvailabilityColor(item.availability) + '20' }]}>
              <Text style={[styles.availabilityText, { color: getAvailabilityColor(item.availability), fontFamily: 'Poppins_600SemiBold' }]}>
                {getAvailabilityText(item.availability)}
              </Text>
            </View>
          </View>
        </View>

        {/* Remove button */}
        <TouchableOpacity
          style={styles.removeButton}
          onPress={() => handleRemoveFavorite(item.worker_id, item.worker_name)}
        >
          <Ionicons name="heart" size={24} color="#EF4444" />
        </TouchableOpacity>
      </View>

      {/* Categories */}
      {item.categories && item.categories.length > 0 && (
        <View style={styles.categoriesContainer}>
          {item.categories.slice(0, 3).map((category, index) => (
            <View key={index} style={[styles.categoryBadge, { backgroundColor: theme.primary + '20' }]}>
              <Text style={[styles.categoryText, { color: theme.primary, fontFamily: 'Poppins_500Medium' }]}>
                {category}
              </Text>
            </View>
          ))}
          {item.categories.length > 3 && (
            <Text style={[styles.moreCategoriesText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              +{item.categories.length - 3} more
            </Text>
          )}
        </View>
      )}

      {/* Stats */}
      <View style={styles.statsRow}>
        <View style={styles.statItem}>
          <Ionicons name="checkmark-circle" size={16} color={theme.primary} />
          <Text style={[styles.statText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
            {item.completed_jobs} completed
          </Text>
        </View>
        
        <View style={styles.statItem}>
          <Ionicons name="cash" size={16} color={theme.primary} />
          <Text style={[styles.statText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
            {item.hourly_rate > 0 ? `${item.hourly_rate.toLocaleString()} TSH/hr` : `${item.daily_rate.toLocaleString()} TSH/day`}
          </Text>
        </View>
      </View>

      {/* Bio preview */}
      {item.bio && (
        <Text
          style={[styles.bioText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}
          numberOfLines={2}
        >
          {item.bio}
        </Text>
      )}
    </TouchableOpacity>
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header title="Favorites" />

      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.titleContainer}>
            <Ionicons name="heart" size={28} color="#EF4444" />
            <Text style={[styles.title, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>{t('favoriteWorkers.favoriteWorkersTitle')}</Text>
          </View>
          
          <Text style={[styles.countText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
            {favorites.length} {favorites.length === 1 ? 'worker' : 'workers'}
          </Text>
        </View>

        {/* List */}
        {loading && page === 1 ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.primary} />
            <Text style={[styles.loadingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{t('favoriteWorkers.loadingFavorites')}</Text>
          </View>
        ) : favorites.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons
              name="heart-outline"
              size={64}
              color={theme.textSecondary}
              style={{ marginBottom: 16 }}
            />
            <Text style={[styles.emptyTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>{t('favoriteWorkers.noFavoritesYet')}</Text>
            <Text style={[styles.emptySubtitle, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{t('favoriteWorkers.browseFavoritesMessage')}</Text>
            <TouchableOpacity
              style={[styles.browseButton, { backgroundColor: theme.primary }]}
              onPress={() => router.push('/(client)/dashboard')}
            >
              <Text style={[styles.browseButtonText, { fontFamily: 'Poppins_600SemiBold' }]}>{t('client.browseWorkers')}</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <FlatList
            data={favorites}
            renderItem={renderWorkerCard}
            keyExtractor={(item) => item.id.toString()}
            contentContainerStyle={styles.listContent}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={theme.primary}
                colors={[theme.primary]}
              />
            }
            onEndReached={handleLoadMore}
            onEndReachedThreshold={0.5}
            ListFooterComponent={
              loading && page > 1 ? (
                <View style={styles.loadMoreContainer}>
                  <ActivityIndicator size="small" color={theme.primary} />
                </View>
              ) : null
            }
          />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  title: {
    fontSize: 24,
  },
  countText: {
    fontSize: 14,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 15,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  emptyTitle: {
    fontSize: 20,
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 15,
    textAlign: 'center',
    marginBottom: 24,
  },
  browseButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  browseButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
  },
  listContent: {
    paddingBottom: 20,
  },
  workerCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  workerHeader: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  workerImage: {
    width: 60,
    height: 60,
    borderRadius: 30,
    marginRight: 12,
  },
  defaultAvatar: {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#E5E7EB',
  },
  workerInfo: {
    flex: 1,
  },
  workerName: {
    fontSize: 17,
    marginBottom: 4,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 4,
  },
  ratingText: {
    fontSize: 15,
  },
  reviewsText: {
    fontSize: 13,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  cityText: {
    fontSize: 13,
  },
  availabilityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  availabilityText: {
    fontSize: 11,
  },
  removeButton: {
    padding: 4,
  },
  categoriesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 12,
  },
  categoryBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  categoryText: {
    fontSize: 12,
  },
  moreCategoriesText: {
    fontSize: 12,
    alignSelf: 'center',
  },
  statsRow: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 8,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statText: {
    fontSize: 13,
  },
  bioText: {
    fontSize: 14,
    lineHeight: 20,
  },
  loadMoreContainer: {
    paddingVertical: 16,
    alignItems: 'center',
  },
});
