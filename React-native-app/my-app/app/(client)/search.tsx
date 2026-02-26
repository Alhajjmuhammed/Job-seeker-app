import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { useDebounce } from '../../hooks/useDebounce';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface Service {
  id: number;
  name: string;
  description: string;
  icon: string;
  available_workers: number;
  avg_completion_days: number;
  avg_budget: number | null;
  completed_projects: number;
  is_available: boolean;
}

export default function ClientServicesScreen() {
  const { theme } = useTheme();
  const { refresh } = useLocalSearchParams();
  const [searchQuery, setSearchQuery] = useState('');
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  
  // Debounce search query to avoid excessive API calls
  const debouncedSearchQuery = useDebounce(searchQuery, 500);

  useEffect(() => {
    let mounted = true;
    const loadServices = async () => {
      try {
        setLoading(true);
        const response = await apiService.getServices();
        if (mounted) {
          setServices(response.services || []);
        }
      } catch (error) {
        console.error('Error loading services:', error);
        if (mounted) {
          Alert.alert('Error', 'Failed to load available services');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadServices();
    return () => { mounted = false; };
  }, [refresh]);

  // Filter services based on search query
  const filteredServices = services.filter(service =>
    service.name.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
    service.description.toLowerCase().includes(debouncedSearchQuery.toLowerCase())
  );

  const handleRequestService = (service: Service) => {
    if (!service.is_available) {
      Alert.alert(
        'Service Unavailable',
        'This service is currently unavailable. Please try again later or contact support.',
        [{ text: 'OK' }]
      );
      return;
    }

    router.push(`/(client)/request-service/${service.id}`);
  };

  const renderServiceCard = (service: Service) => (
    <TouchableOpacity
      key={service.id}
      style={[styles.serviceCard, { backgroundColor: theme.card }]}
      onPress={() => handleRequestService(service)}
      activeOpacity={0.7}
    >
      <View style={styles.serviceHeader}>
        <View style={styles.serviceIconContainer}>
          <Ionicons 
            name={service.icon as any || 'construct'} 
            size={32} 
            color={service.is_available ? theme.primary : theme.textSecondary} 
          />
        </View>
        <View style={styles.serviceInfo}>
          <Text style={[styles.serviceName, { color: theme.text }]}>{service.name}</Text>
          <Text style={[styles.serviceDescription, { color: theme.textSecondary }]} numberOfLines={2}>
            {service.description}
          </Text>
        </View>
        {service.is_available ? (
          <View style={[styles.availableBadge, { backgroundColor: '#D1FAE5' }]}>
            <Text style={styles.availableBadgeText}>Available</Text>
          </View>
        ) : (
          <View style={[styles.unavailableBadge, { backgroundColor: '#FEE2E2' }]}>
            <Text style={styles.unavailableBadgeText}>Unavailable</Text>
          </View>
        )}
      </View>

      <View style={styles.serviceStats}>
        <View style={styles.statItem}>
          <Ionicons name="people" size={16} color={theme.textSecondary} />
          <Text style={[styles.statText, { color: theme.textSecondary }]}>
            {service.available_workers} workers available
          </Text>
        </View>
        
        {service.completed_projects > 0 && (
          <View style={styles.statItem}>
            <Ionicons name="checkmark-circle" size={16} color="#10B981" />
            <Text style={[styles.statText, { color: theme.textSecondary }]}>
              {service.completed_projects} completed
            </Text>
          </View>
        )}
        
        {service.avg_completion_days > 0 && (
          <View style={styles.statItem}>
            <Ionicons name="time" size={16} color={theme.textSecondary} />
            <Text style={[styles.statText, { color: theme.textSecondary }]}>
              ~{service.avg_completion_days} days
            </Text>
          </View>
        )}
      </View>

      <View style={styles.serviceFooter}>
        <Text style={[styles.requestButtonText, { color: theme.primary }]}>
          {service.is_available ? 'Request This Service' : 'Currently Unavailable'}
        </Text>
        <Ionicons name="arrow-forward" size={16} color={theme.primary} />
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Request Services" showBack={false} />

      {/* Search Bar */}
      <View style={[styles.searchContainer, { backgroundColor: theme.card, borderBottomColor: theme.border }]}>
        <View style={[styles.searchInputContainer, { backgroundColor: theme.background }]}>
          <Ionicons name="search" size={20} color={theme.textSecondary} />
          <TextInput
            style={[styles.searchInput, { color: theme.text }]}
            placeholder="Search services..."
            placeholderTextColor={theme.textSecondary}
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.primary} />
            <Text style={[styles.loadingText, { color: theme.textSecondary }]}>
              Loading available services...
            </Text>
          </View>
        ) : (
          <>
            <View style={[styles.infoCard, { backgroundColor: theme.card }]}>
              <Ionicons name="information-circle" size={24} color={theme.primary} />
              <Text style={[styles.infoText, { color: theme.textSecondary }]}>
                Select a service below and our team will assign the most qualified worker to handle your request.
              </Text>
            </View>

            <Text style={[styles.resultsText, { color: theme.textSecondary }]}>
              {filteredServices.length} service{filteredServices.length !== 1 ? 's' : ''} available
            </Text>

            {filteredServices.map(renderServiceCard)}
          </>
        )}
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
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 60,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
  },
  infoCard: {
    flexDirection: 'row',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    alignItems: 'flex-start',
  },
  infoText: {
    flex: 1,
    marginLeft: 12,
    fontSize: 14,
    lineHeight: 20,
  },
  resultsText: {
    fontSize: 14,
    marginBottom: 16,
  },
  serviceCard: {
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  serviceHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  serviceIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F3F4F6',
    marginRight: 12,
  },
  serviceInfo: {
    flex: 1,
  },
  serviceName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  serviceDescription: {
    fontSize: 14,
    lineHeight: 20,
  },
  availableBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  availableBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#065F46',
  },
  unavailableBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  unavailableBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#DC2626',
  },
  serviceStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 12,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statText: {
    marginLeft: 6,
    fontSize: 13,
  },
  serviceFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  requestButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
});
