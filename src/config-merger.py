import os

import yaml

kubeconfig_files = os.listdir()

if 'config-merger.py' in kubeconfig_files:
    kubeconfig_files.remove('config-merger.py')


def get_kubeconfigs():
    """
    Читает все kubeconfig файлы и извлекает из них contexts, clusters и users
    Теперь добавляет информацию о файле-источнике
    """
    contexts = []
    clusters = []
    users = []

    for file in kubeconfig_files:
        try:
            with open(file, 'r') as f:
                file_content = yaml.load(f, Loader=yaml.FullLoader)

                file_basename = os.path.splitext(file)[0]

                if 'clusters' in file_content:
                    for cluster in file_content['clusters']:
                        cluster_copy = cluster.copy()
                        cluster_copy['original_name'] = cluster['name']
                        cluster_copy['source_file'] = file_basename
                        cluster_copy['name'] = f"{cluster['name']}-{file_basename}"
                        clusters.append(cluster_copy)

                if 'users' in file_content:
                    for user in file_content['users']:
                        user_copy = user.copy()
                        user_copy['original_name'] = user['name']
                        user_copy['source_file'] = file_basename
                        user_copy['name'] = f"{user['name']}-{file_basename}"
                        users.append(user_copy)

                if 'contexts' in file_content:
                    for context in file_content['contexts']:
                        context_copy = context.copy()
                        context_copy['context'] = context['context'].copy()
                        context_copy['original_name'] = context['name']
                        context_copy['source_file'] = file_basename
                        context_copy['name'] = f"{context['name']}-{file_basename}"
                        context_copy['context']['cluster'] = f"{context['context']['cluster']}-{file_basename}"
                        context_copy['context']['user'] = f"{context['context']['user']}-{file_basename}"
                        contexts.append(context_copy)

        except yaml.YAMLError as e:
            print(f'Ошибка при чтении файла {file}: {e}')
        except Exception as e:
            print(f'Неожиданная ошибка с файлом {file}: {e}')

    return contexts, clusters, users


def create_unique_name(base_name, existing_names):
    """
    Создает уникальное имя, добавляя числовой суффикс
    Пример: если 'prod' уже существует, вернет 'prod-1', 'prod-2' и т.д.
    """
    counter = 1
    new_name = base_name

    while new_name in existing_names:
        new_name = f"{base_name}-{counter}"
        counter += 1

    return new_name


def rename_clusters(clusters):
    """
    Переименовывает кластеры с дублирующимися именами
    Возвращает обработанные кластеры и mapping старых имен к новым
    """
    unique_clusters = []
    cluster_mapping = {}
    existing_names = set()

    for cluster in clusters:
        original_name = cluster['name']

        if original_name in existing_names:
            new_name = create_unique_name(original_name, existing_names)

            cluster_mapping[original_name] = new_name

            cluster = cluster.copy()
            cluster['name'] = new_name
        else:

            cluster_mapping[original_name] = original_name

        existing_names.add(cluster['name'])
        unique_clusters.append(cluster)

    return unique_clusters, cluster_mapping


def rename_users(users):
    """
    Переименовывает пользователей с дублирующимися именами
    Возвращает обработанных пользователей и mapping старых имен к новым
    """
    unique_users = []
    user_mapping = {}
    existing_names = set()

    for user in users:
        original_name = user['name']

        if original_name in existing_names:
            new_name = create_unique_name(original_name, existing_names)
            user_mapping[original_name] = new_name
            user = user.copy()
            user['name'] = new_name
        else:
            user_mapping[original_name] = original_name

        existing_names.add(user['name'])
        unique_users.append(user)

    return unique_users, user_mapping


def rename_contexts(contexts, cluster_mapping, user_mapping):
    """
    Обрабатывает контексты:
    1. Переименовывает дублирующиеся имена контекстов
    2. Обновляет ссылки на переименованные кластеры и пользователей
    """
    unique_contexts = []
    existing_names = set()

    for context in contexts:

        processed_context = context.copy()
        processed_context['context'] = context['context'].copy()

        original_name = processed_context['name']

        context_details = processed_context['context']

        old_cluster_name = context_details['cluster']
        if old_cluster_name in cluster_mapping:
            context_details['cluster'] = cluster_mapping[old_cluster_name]

        old_user_name = context_details['user']
        if old_user_name in user_mapping:
            context_details['user'] = user_mapping[old_user_name]

        if original_name in existing_names:

            new_context_name = create_unique_name(original_name, existing_names)
            processed_context['name'] = new_context_name
            existing_names.add(new_context_name)
        else:
            existing_names.add(original_name)

        unique_contexts.append(processed_context)

    return unique_contexts


def merge_kubeconfigs():
    """
    Главная функция, которая объединяет все kubeconfig файлы
    """

    print("Чтение kubeconfig файлов...")
    contexts, clusters, users = get_kubeconfigs()
    print(f"Найдено: {len(contexts)} контекстов, {len(clusters)} кластеров, {len(users)} пользователей")

    print("\nОбработка кластеров...")
    unique_clusters, cluster_mapping = rename_clusters(clusters)
    print(f"После обработки: {len(unique_clusters)} уникальных кластеров")

    print("\nОбработка пользователей...")
    unique_users, user_mapping = rename_users(users)
    print(f"После обработки: {len(unique_users)} уникальных пользователей")

    print("\nОбработка контекстов...")
    unique_contexts = rename_contexts(contexts, cluster_mapping, user_mapping)
    print(f"После обработки: {len(unique_contexts)} уникальных контекстов")

    result = {
        'apiVersion': 'v1',
        'kind': 'Config',
        'clusters': unique_clusters,
        'users': unique_users,
        'contexts': unique_contexts,
    }

    if unique_contexts:
        result['current-context'] = unique_contexts[0]['name']

    return result


def save_config(config, filename='config'):
    """
    Сохраняет объединенный kubeconfig в файл
    """
    try:
        with open(filename, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"\nКонфиг сохранен в файл: {filename}")
        print(f"Обработано::")
        print(f"  - Кластеры: {len(config['clusters'])}")
        print(f"  - Пользователи: {len(config['users'])}")
        print(f"  - Контексты: {len(config['contexts'])}")
        if 'current-context' in config:
            print(f"  - Текущий контекст: {config['current-context']}")
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")


if __name__ == '__main__':
    merged_config = merge_kubeconfigs()

    save_config(merged_config)
