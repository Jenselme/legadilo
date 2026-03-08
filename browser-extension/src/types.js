/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * @typedef {Object} Tag
 * @property {string} slug
 * @property {string} title
 * @property {Tag[]} sub_tags
 */

/**
 * @typedef {Object} Category
 * @property {number} id
 * @property {string} title
 */

/**
 * @typedef {Object} Article
 * @property {number} id
 * @property {string} title
 * @property {number} reading_time
 * @property {Tag[]} tags
 * @property {boolean} is_read
 * @property {boolean} is_favorite
 * @property {boolean} is_for_later
 * @property {string} details_url
 */

/**
 * @typedef {Object} Feed
 * @property {number} id
 * @property {string} title
 * @property {string} feed_url
 * @property {number} refresh_delay
 * @property {number} article_retention_time
 * @property {string} details_url
 * @property {boolean} enabled
 * @property {Category | null} category
 * @property {Tag[]} tags
 */

/**
 * @typedef {Object} Options
 * @property {string} instanceUrl
 * @property {string} userEmail
 * @property {string} tokenId
 * @property {string} tokenSecret
 * @property {string} accessToken
 */

/**
 * @typedef {Object} SaveArticlePayload
 * @property {string} url
 * @property {string} title
 * @property {string} content
 * @property {string} contentType
 * @property {string} language
 * @property {boolean} mustExtractContent
 */

/**
 * @typedef {Object} UpdateArticlePayload
 * @property {string} title
 * @property {string[]} tags
 * @property {string | null} readAt
 * @property {boolean} isFavorite
 * @property {boolean} isForLater
 * @property {number} readingTime
 */

/**
 * @typedef {Object} UpdateFeedPayload
 * @property {number | null} [categoryId]
 * @property {string[]} [tags]
 * @property {string} [refreshDelay]
 * @property {number} [articleRetentionTime]
 * @property {string | null} [disabledAt]
 * @property {string | null} [disabledReason]
 */

/**
 * @typedef {Object} SubscribeToFeedPayload
 * @property {string} link
 */

export {};
