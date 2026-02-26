import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

export default function TermsScreen() {
  const { theme } = useTheme();
  const [termsContent, setTermsContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTermsContent();
  }, []);

  const loadTermsContent = async () => {
    try {
      const response = await apiService.getTermsOfService();
      setTermsContent(response.content || 'Terms of service not available.');
    } catch (error) {
      console.error('Error loading terms:', error);
      Alert.alert('Error', 'Failed to load terms of service');
      setTermsContent('Failed to load terms of service. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={[styles.loadingText, { color: theme.text }]}>
          Loading terms of service...
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Terms of Service" showBack />
      
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <View style={[styles.contentContainer, { backgroundColor: theme.card }]}>
          <Text style={[styles.title, { color: theme.text }]}>
            Terms of Service
          </Text>
          
          <Text style={[styles.lastUpdated, { color: theme.textSecondary }]}>
            Last updated: {new Date().toLocaleDateString()}
          </Text>
          
          <Text style={[styles.contentText, { color: theme.text }]}>
            {termsContent}
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 16,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
  contentContainer: {
    padding: 20,
    borderRadius: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
    textAlign: 'center',
  },
  lastUpdated: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 24,
  },
  contentText: {
    fontSize: 16,
    lineHeight: 24,
    textAlign: 'justify',
  },
});