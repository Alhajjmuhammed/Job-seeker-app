import { useEffect } from 'react';
import { Redirect } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native';

export default function Index() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#0F766E" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  if (!user) {
    return <Redirect href="/(auth)/login" />;
  }

  // Redirect based on user type
  if (user.userType === 'worker') {
    return <Redirect href="/(worker)/dashboard" />;
  } else if (user.userType === 'client') {
    return <Redirect href="/(client)/dashboard" />;
  }

  // Fallback to login if userType is unknown
  return <Redirect href="/(auth)/login" />;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#6B7280',
  },
});
