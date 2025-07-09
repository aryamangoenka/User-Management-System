"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { Users, Shield, Settings, Database, Key, Globe } from "lucide-react";

export default function HomePage() {
  const { user } = useAuth();

  const features = [
    {
      icon: Users,
      title: "User Management",
      description:
        "Complete CRUD operations for user accounts with role-based access control.",
    },
    {
      icon: Shield,
      title: "Authentication",
      description:
        "Secure token-based authentication with JWT and session management.",
    },
    {
      icon: Database,
      title: "REST API",
      description:
        "Full-featured REST API with proper endpoints and data validation.",
    },
    {
      icon: Globe,
      title: "Modern UI",
      description:
        "Beautiful, responsive interface built with Next.js and Tailwind CSS.",
    },
    {
      icon: Key,
      title: "Role-Based Access",
      description:
        "Different permission levels: Admin, Manager, User, and Staff roles.",
    },
    {
      icon: Settings,
      title: "Profile Management",
      description:
        "Users can manage their profiles, update information, and preferences.",
    },
  ];

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center space-y-6">
        <div className="space-y-4">
          <Badge variant="secondary" className="px-4 py-1">
            Next.js + Django + TypeScript
          </Badge>
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
            User Management
            <span className="text-blue-600"> System</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            A modern, full-stack user management solution with authentication,
            role-based access control, and a beautiful interface.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {user ? (
            <>
              <Button size="lg" asChild>
                <Link href="/profile">Go to Profile</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/users">Manage Users</Link>
              </Button>
            </>
          ) : (
            <>
              <Button size="lg" asChild>
                <Link href="/register">Get Started</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/login">Sign In</Link>
              </Button>
            </>
          )}
        </div>
      </section>

      {/* User Status */}
      {user && (
        <section>
          <Card className="max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Welcome Back!
              </CardTitle>
              <CardDescription>
                You are logged in as {user.first_name} {user.last_name}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-medium text-gray-500">Role</p>
                  <Badge variant="outline" className="mt-1">
                    {user.role}
                  </Badge>
                </div>
                <div>
                  <p className="font-medium text-gray-500">Status</p>
                  <Badge
                    variant={user.is_active ? "default" : "destructive"}
                    className="mt-1"
                  >
                    {user.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
                <div>
                  <p className="font-medium text-gray-500">Email</p>
                  <p className="mt-1">{user.email}</p>
                </div>
                <div>
                  <p className="font-medium text-gray-500">Member Since</p>
                  <p className="mt-1">
                    {new Date(user.date_joined).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {/* Features Section */}
      <section className="space-y-8">
        <div className="text-center space-y-4">
          <h2 className="text-3xl font-bold text-gray-900">Features</h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Everything you need for modern user management and authentication.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Icon className="h-5 w-5 text-blue-600" />
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm leading-relaxed">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* API Section */}
      <section className="bg-gray-50 rounded-lg p-8">
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-bold text-gray-900">
            REST API Available
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Our system provides a comprehensive REST API for integration with
            other applications.
          </p>
          <div className="bg-white rounded-lg p-4 border font-mono text-sm text-left max-w-lg mx-auto">
            <p className="text-green-600">GET /api/v1/users/</p>
            <p className="text-blue-600">POST /api/v1/auth/login/</p>
            <p className="text-purple-600">PUT /api/v1/profile/update/</p>
            <p className="text-red-600">DELETE /api/v1/users/{`{id}`}/</p>
          </div>
          <Button variant="outline" asChild>
            <Link href="http://127.0.0.1:8000/api/v1/" target="_blank">
              Explore API
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
